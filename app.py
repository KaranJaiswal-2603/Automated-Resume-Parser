
"""Flask web application for the Automated Resume Parser."""

import hashlib
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from parser import parse_resume
from database import (
    delete_candidate,
    ensure_schema,
    find_duplicate_resume,
    get_candidate_by_id,
    query_candidates,
    save_parsed_candidate,
    update_candidate,
)

# Load variables from the local .env file
load_dotenv()

# Initialize Flask
app = Flask(__name__)

# Read the secret key from .env
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# Stop safely if the secret key is missing
if not app.secret_key:
    raise RuntimeError(
        "FLASK_SECRET_KEY is missing. Add it to your .env file."
    )

# Maximum upload size: 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {"pdf", "docx"}
_schema_ready = False



@app.before_request
def initialize_database_once():
    """Initialize or update the database schema before handling requests."""
    global _schema_ready

    if not _schema_ready:
        ensure_schema()
        _schema_ready = True


def allowed_file(filename):
    """Return True when the filename has an allowed extension."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def candidate_fields(candidate):
    """Convert a database row into a template-friendly dictionary."""
    return {
        "id": candidate[0],
        "full_name": candidate[1] or "",
        "email": candidate[2] or "",
        "phone": candidate[3] or "",
        "skills": candidate[4] or [],
        "education": candidate[5] or [],
        "experience": candidate[6] or [],
    }


@app.errorhandler(413)
def file_too_large(_error):
    """Handle uploads exceeding Flask's request-size limit."""
    flash("File size must not exceed 10 MB.", "error")
    return redirect(url_for("home"))


@app.route("/")
def home():
    """Display the resume upload page."""
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_resume():
    """Validate, parse, and save an uploaded resume."""
    file = request.files.get("resume")

    if file is None or not file.filename:
        flash("Please select a resume file.", "error")
        return redirect(url_for("home"))

    filename = secure_filename(file.filename)

    if not filename or not allowed_file(filename):
        flash("Only PDF and DOCX files are allowed.", "error")
        return redirect(url_for("home"))

    file_bytes = file.read(app.config["MAX_CONTENT_LENGTH"] + 1)

    if not file_bytes:
        flash("The selected file is empty.", "error")
        return redirect(url_for("home"))

    if len(file_bytes) > app.config["MAX_CONTENT_LENGTH"]:
        flash("File size must not exceed 10 MB.", "error")
        return redirect(url_for("home"))

    resume_hash = hashlib.sha256(file_bytes).hexdigest()
    temp_path = None

    try:
        duplicate = find_duplicate_resume(resume_hash)

        if duplicate:
            flash(
                "This exact resume was already uploaded for "
                f"candidate #{duplicate[0]}.",
                "error",
            )
            return redirect(
                url_for(
                    "candidate_detail",
                    candidate_id=duplicate[0],
                )
            )

        try:
            with tempfile.NamedTemporaryFile(
                suffix=Path(filename).suffix.lower(),
                delete=False,
            ) as temp_file:
                temp_file.write(file_bytes)
                temp_path = temp_file.name

            candidate = parse_resume(temp_path)

            if not candidate.get("full_name") and not candidate.get("email"):
                flash(
                    "The parser could not identify a name or email. "
                    "Please check the resume.",
                    "error",
                )
                return redirect(url_for("home"))

            candidate_id = save_parsed_candidate(
                candidate,
                resume_filename=filename,
                resume_sha256=resume_hash,
            )

        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

        flash("Resume parsed and saved successfully.", "success")

        return render_template(
            "result.html",
            candidate=candidate,
            candidate_id=candidate_id,
        )

    except Exception:
        app.logger.exception("Resume processing failed")
        flash(
            "Resume processing failed. Check that the file contains "
            "readable text and the database is available.",
            "error",
        )
        return redirect(url_for("home"))


@app.route("/dashboard")
def dashboard():
    """Display searchable, filterable, sortable, paginated candidates."""
    search_term = request.args.get("q", "").strip()
    skill = request.args.get("skill", "").strip()
    education = request.args.get("education", "").strip()
    experience = request.args.get("experience", "").strip()
    sort_by = request.args.get("sort_by", "newest")

    try:
        page = max(int(request.args.get("page", "1")), 1)
    except (ValueError, TypeError):
        page = 1

    per_page = 10

    candidates, total = query_candidates(
        search_term=search_term,
        skill=skill,
        education=education,
        experience=experience,
        sort_by=sort_by,
        page=page,
        per_page=per_page,
    )

    total_pages = max((total + per_page - 1) // per_page, 1)

    if page > total_pages:
        return redirect(
            url_for(
                "dashboard",
                q=search_term,
                skill=skill,
                education=education,
                experience=experience,
                sort_by=sort_by,
                page=total_pages,
            )
        )

    return render_template(
        "dashboard.html",
        candidates=candidates,
        search_term=search_term,
        skill=skill,
        education_filter=education,
        experience_filter=experience,
        sort_by=sort_by,
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        start_index=(page - 1) * per_page + 1 if total else 0,
        end_index=min(page * per_page, total),
    )


@app.route("/candidate/<int:candidate_id>")
def candidate_detail(candidate_id):
    """Display an individual candidate profile."""
    candidate = get_candidate_by_id(candidate_id)

    if candidate is None:
        return "Candidate not found.", 404

    return render_template(
        "candidate_detail.html",
        candidate=candidate,
    )


@app.route("/candidate/<int:candidate_id>/edit", methods=["GET", "POST"])
def edit_candidate(candidate_id):
    """Display and process candidate edits."""
    candidate = get_candidate_by_id(candidate_id)

    if candidate is None:
        return "Candidate not found.", 404

    fields = candidate_fields(candidate)

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        skills = request.form.get("skills", "")
        education = request.form.get("education", "")
        experience = request.form.get("experience", "")

        fields.update(
            {
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "skills": [
                    item.strip()
                    for item in skills.split(",")
                    if item.strip()
                ],
                "education": [
                    item.strip()
                    for item in education.splitlines()
                    if item.strip()
                ],
                "experience": [
                    item.strip()
                    for item in experience.splitlines()
                    if item.strip()
                ],
            }
        )

        if not full_name:
            flash("Candidate name is required.", "error")
            return render_template(
                "edit_candidate.html",
                candidate=fields,
            ), 400

        try:
            updated = update_candidate(
                candidate_id,
                full_name,
                email,
                phone,
                skills,
                education,
                experience,
            )

            if not updated:
                return "Candidate not found.", 404

            flash(
                "Candidate details updated successfully.",
                "success",
            )
            return redirect(
                url_for(
                    "candidate_detail",
                    candidate_id=candidate_id,
                )
            )

        except Exception:
            app.logger.exception("Candidate update failed")
            flash(
                "Could not update candidate details. Please try again.",
                "error",
            )
            return render_template(
                "edit_candidate.html",
                candidate=fields,
            ), 500

    return render_template(
        "edit_candidate.html",
        candidate=fields,
    )


@app.route("/candidate/<int:candidate_id>/delete", methods=["POST"])
def remove_candidate(candidate_id):
    """Delete a candidate after an explicit POST request."""
    try:
        if not delete_candidate(candidate_id):
            return "Candidate not found.", 404

        flash("Candidate deleted successfully.", "success")
        return redirect(url_for("dashboard"))

    except Exception:
        app.logger.exception("Candidate deletion failed")
        flash("Could not delete candidate.", "error")
        return redirect(url_for("dashboard"))


if __name__ == "__main__":
    ensure_schema()

    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
    )
