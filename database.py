
"""PostgreSQL data access for the Automated Resume Parser."""

import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Create a PostgreSQL database connection."""
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "resume_parser"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def ensure_schema():
    """Create the table and safely add columns required by this version."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS candidates (
                    id SERIAL PRIMARY KEY,
                    full_name VARCHAR(255),
                    email VARCHAR(320),
                    phone VARCHAR(50),
                    skills TEXT[] NOT NULL DEFAULT '{}',
                    education TEXT[] NOT NULL DEFAULT '{}',
                    experience TEXT[] NOT NULL DEFAULT '{}'
                )
            """)

            cur.execute("""
                ALTER TABLE candidates
                ADD COLUMN IF NOT EXISTS experience
                TEXT[] NOT NULL DEFAULT '{}'
            """)
            cur.execute("""
                ALTER TABLE candidates
                ADD COLUMN IF NOT EXISTS resume_filename TEXT
            """)
            cur.execute("""
                ALTER TABLE candidates
                ADD COLUMN IF NOT EXISTS resume_sha256 CHAR(64)
            """)
            cur.execute("""
                ALTER TABLE candidates
                ADD COLUMN IF NOT EXISTS created_at
                TIMESTAMPTZ NOT NULL DEFAULT NOW()
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_candidates_created_at
                ON candidates (created_at DESC)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_candidates_resume_sha256
                ON candidates (resume_sha256)
            """)


def normalize_list(value, separator=","):
    """Convert text or an iterable into a list of clean strings."""
    if value is None:
        return []

    if isinstance(value, str):
        return [
            part.strip()
            for part in value.split(separator)
            if part.strip()
        ]

    return [
        str(part).strip()
        for part in value
        if str(part).strip()
    ]


def insert_candidate(
    full_name,
    email,
    phone,
    skills,
    education,
    experience=None,
    resume_filename=None,
    resume_sha256=None,
):
    """Insert a candidate and return the new candidate ID."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO candidates (
                    full_name, email, phone, skills, education,
                    experience, resume_filename, resume_sha256
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                full_name,
                email,
                phone,
                normalize_list(skills),
                normalize_list(education, separator="\n"),
                normalize_list(experience, separator="\n"),
                resume_filename,
                resume_sha256,
            ))

            return cur.fetchone()[0]


def save_parsed_candidate(
    candidate,
    resume_filename=None,
    resume_sha256=None,
):
    """Save fields returned by parse_resume()."""
    return insert_candidate(
        full_name=candidate.get("full_name"),
        email=candidate.get("email"),
        phone=candidate.get("phone"),
        skills=candidate.get("skills", []),
        education=candidate.get("education", []),
        experience=candidate.get("experience", []),
        resume_filename=resume_filename,
        resume_sha256=resume_sha256,
    )


def find_duplicate_resume(resume_sha256):
    """Find an existing record with the same uploaded file hash."""
    if not resume_sha256:
        return None

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, full_name
                FROM candidates
                WHERE resume_sha256 = %s
                ORDER BY id DESC
                LIMIT 1
            """, (resume_sha256,))

            return cur.fetchone()


def _candidate_select():
    """Return the common dashboard selection."""
    return """
        SELECT id, full_name, email, phone,
               skills, education, experience,
               resume_filename, created_at
        FROM candidates
    """


def get_candidates():
    """Return all candidates, newest first."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                _candidate_select() + " ORDER BY id DESC"
            )
            return cur.fetchall()


def get_candidate_by_id(candidate_id):
    """Return one candidate as a seven-field tuple."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, full_name, email, phone,
                       skills, education, experience
                FROM candidates
                WHERE id = %s
            """, (candidate_id,))

            return cur.fetchone()


def _conditions(
    search_term="",
    skill="",
    education="",
    experience="",
):
    """Build parameterized conditions for candidate queries."""
    clauses = []
    params = []

    if search_term.strip():
        pattern = f"%{search_term.strip()}%"

        clauses.append("""
            (
                COALESCE(full_name, '') ILIKE %s
                OR COALESCE(email, '') ILIKE %s
                OR COALESCE(phone, '') ILIKE %s
                OR COALESCE(resume_filename, '') ILIKE %s

                OR EXISTS (
                    SELECT 1
                    FROM unnest(
                        COALESCE(skills, ARRAY[]::TEXT[])
                    ) AS items(value)
                    WHERE value ILIKE %s
                )

                OR EXISTS (
                    SELECT 1
                    FROM unnest(
                        COALESCE(education, ARRAY[]::TEXT[])
                    ) AS items(value)
                    WHERE value ILIKE %s
                )

                OR EXISTS (
                    SELECT 1
                    FROM unnest(
                        COALESCE(experience, ARRAY[]::TEXT[])
                    ) AS items(value)
                    WHERE value ILIKE %s
                )
            )
        """)

        params.extend([pattern] * 7)

    filters = (
        ("skills", skill),
        ("education", education),
        ("experience", experience),
    )

    # Column names are fixed above, never supplied by the user.
    for column, value in filters:
        if value.strip():
            clauses.append(f"""
                EXISTS (
                    SELECT 1
                    FROM unnest(
                        COALESCE({column}, ARRAY[]::TEXT[])
                    ) AS items(value)
                    WHERE value ILIKE %s
                )
            """)
            params.append(f"%{value.strip()}%")

    where_sql = (
        " WHERE " + " AND ".join(clauses)
        if clauses
        else ""
    )

    return where_sql, params


def query_candidates(
    search_term="",
    skill="",
    education="",
    experience="",
    sort_by="newest",
    page=1,
    per_page=10,
):
    """Return a page of candidates and the total matching count."""
    order_options = {
        "newest": "id DESC",
        "oldest": "id ASC",
        "name_asc": "full_name ASC NULLS LAST, id DESC",
        "name_desc": "full_name DESC NULLS LAST, id DESC",
    }

    # Prevent arbitrary SQL from being used as an order expression.
    order_clause = order_options.get(
        sort_by,
        order_options["newest"],
    )

    page = max(int(page), 1)
    per_page = min(max(int(per_page), 1), 100)

    where_sql, params = _conditions(
        search_term=search_term,
        skill=skill,
        education=education,
        experience=experience,
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM candidates" + where_sql,
                params,
            )
            total = cur.fetchone()[0]

            cur.execute(
                _candidate_select()
                + where_sql
                + f" ORDER BY {order_clause} LIMIT %s OFFSET %s",
                params + [
                    per_page,
                    (page - 1) * per_page,
                ],
            )

            rows = cur.fetchall()

    return rows, total


def search_candidates(search_term=""):
    """Compatibility helper for earlier project code."""
    rows, _ = query_candidates(
        search_term=search_term,
        per_page=100,
    )
    return rows


def filter_candidates(
    skill="",
    education="",
    experience="",
    sort_by="newest",
):
    """Compatibility helper for separate filters."""
    rows, _ = query_candidates(
        skill=skill,
        education=education,
        experience=experience,
        sort_by=sort_by,
        per_page=100,
    )
    return rows


def update_candidate(
    candidate_id,
    full_name,
    email,
    phone,
    skills,
    education,
    experience=None,
):
    """Update candidate details without overwriting metadata."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            if experience is None:
                cur.execute("""
                    UPDATE candidates
                    SET full_name = %s,
                        email = %s,
                        phone = %s,
                        skills = %s,
                        education = %s
                    WHERE id = %s
                    RETURNING id
                """, (
                    full_name,
                    email,
                    phone,
                    normalize_list(skills),
                    normalize_list(education, separator="\n"),
                    candidate_id,
                ))
            else:
                cur.execute("""
                    UPDATE candidates
                    SET full_name = %s,
                        email = %s,
                        phone = %s,
                        skills = %s,
                        education = %s,
                        experience = %s
                    WHERE id = %s
                    RETURNING id
                """, (
                    full_name,
                    email,
                    phone,
                    normalize_list(skills),
                    normalize_list(education, separator="\n"),
                    normalize_list(experience, separator="\n"),
                    candidate_id,
                ))

            return cur.fetchone() is not None


def delete_candidate(candidate_id):
    """Delete a candidate and return whether a row was removed."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM candidates
                WHERE id = %s
                RETURNING id
            """, (candidate_id,))

            return cur.fetchone() is not None


def get_dashboard_stats():
    """Return total candidates and counts with skills or experience."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*),
                    COUNT(*) FILTER (
                        WHERE COALESCE(cardinality(skills), 0) > 0
                    ),
                    COUNT(*) FILTER (
                        WHERE COALESCE(cardinality(experience), 0) > 0
                    )
                FROM candidates
            """)

            return cur.fetchone()


if __name__ == "__main__":
    try:
        ensure_schema()
        print("Database schema ready.")
        print("Candidate count:", get_dashboard_stats()[0])
    except Exception as exc:
        print("Database test failed:", exc)
