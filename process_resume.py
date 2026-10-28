
"""Process a resume from the command line."""

from pathlib import Path

from parser import parse_resume
from database import ensure_schema, save_parsed_candidate


def process_resume_file(resume_path):
    """Parse a resume and optionally save it to PostgreSQL."""
    path = Path(resume_path)

    if not path.is_file():
        raise FileNotFoundError(f"Resume not found: {path}")

    print("\nProcessing resume...")

    candidate = parse_resume(path)

    print("\n--- EXTRACTED CANDIDATE DETAILS ---")
    for field, value in candidate.items():
        print(f"{field}: {value}")

    if not candidate.get("full_name") and not candidate.get("email"):
        raise ValueError(
            "Could not identify a candidate name or email. "
            "Please check the extracted information."
        )

    confirm = input(
        "\nSave these details to PostgreSQL? (y/n): "
    ).strip().lower()

    if confirm != "y":
        print("Save cancelled.")
        return

    candidate_id = save_parsed_candidate(
        candidate,
        resume_filename=path.name,
    )

    print("\nCandidate saved successfully!")
    print(f"Candidate ID: {candidate_id}")


if __name__ == "__main__":
    resume_path = input(
        "Enter the full path to the resume: "
    ).strip().strip('"')

    try:
        ensure_schema()
        process_resume_file(resume_path)
    except Exception as error:
        print(f"\nProcessing failed: {error}")
