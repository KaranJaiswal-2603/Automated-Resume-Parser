# Automated Resume Parser

A web-based resume parsing application built with **Python, Flask, spaCy, PDFPlumber, and PostgreSQL**. The system extracts candidate information from resumes and stores it in a searchable database for easier candidate management.

## Overview

Recruiters and users often need to review multiple resumes manually to identify candidate details. The Automated Resume Parser simplifies this process by extracting relevant information from uploaded resumes and organizing it in a centralized database.

The application provides a web interface for uploading resumes, reviewing extracted information, searching candidate records, and managing stored profiles.

## Features

- **Resume Upload:** Upload PDF and DOCX resume files through the web interface.
- **Information Extraction:** Extract candidate names, email addresses, phone numbers, skills, education, and available work experience.
- **Resume Parsing:** Use Python, spaCy, and PDFPlumber to process resume content.
- **Database Storage:** Store candidate information in PostgreSQL.
- **Search and Filtering:** Find candidates using available search and filter options.
- **Candidate Profiles:** View individual candidate details.
- **Candidate Management:** Edit and delete stored candidate records.
- **Duplicate Detection:** Detect identical resume files when duplicate checking is enabled in the application.
- **Dashboard:** View and manage candidate records through a Flask-powered interface.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Application logic and resume processing |
| Flask | Web application and routing |
| spaCy | Natural language processing |
| PDFPlumber | Extract text from PDF documents |
| python-docx | Read DOCX documents |
| PostgreSQL | Store candidate information |
| psycopg | Connect Python to PostgreSQL |
| HTML and CSS | User interface and styling |
| JavaScript | Client-side interactions |

## Project Structure

```text
Automated_Resume_Parser/
├── app.py
├── parser.py
├── database.py
├── process_resume.py
├── requirements.txt
├── .gitignore
├── README.md
├── templates/
│   ├── index.html
│   ├── result.html
│   ├── dashboard.html
│   ├── candidate_detail.html
│   └── edit_candidate.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── script.js
```

## Prerequisites

Before running the application, install or configure:

- Python 3.11 or another Python version compatible with your installed dependencies
- PostgreSQL
- Git (optional, for version control)
- pip, the Python package installer

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/KaranJaiswal-2603/Automated-Resume-Parser
cd Automated_Resume_Parser
```

Replace `YOUR_GITHUB_REPOSITORY_URL` with the HTTPS URL of your GitHub repository.

Alternatively, download the repository as a ZIP file and extract it.

### 2. Create a Virtual Environment

**Windows PowerShell:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If you use Command Prompt instead:

```bat
venv\Scripts\activate.bat
```

### 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Install the spaCy Language Model

```bash
python -m spacy download en_core_web_sm
```

### 5. Configure PostgreSQL

Install and start PostgreSQL, then create a database named `resume_parser` if that is the database name configured in your application.

Example SQL:

```sql
CREATE DATABASE resume_parser;
```

Configure the database connection settings expected by `database.py`.

### 6. Configure Environment Variables

Create a local `.env` file in the project root. Add your Flask secret key and the PostgreSQL connection settings required by your application's `database.py`.

Example:

```env
FLASK_SECRET_KEY=your_generated_secret_key
```

Add the appropriate database variables using the names expected by your current code.

**Security:** Never commit `.env` or publish database passwords, secret keys, or private candidate resumes to GitHub.

### 7. Run the Application

```bash
python app.py
```

Open the following address in your browser:

```text
http://127.0.0.1:5000
```

The application runs locally on your computer.

## How to Use

1. Open the application in your browser.
2. Upload a supported PDF or DOCX resume.
3. Allow the application to extract the available candidate information.
4. Review the parsed information.
5. Open the candidate dashboard to search, filter, and manage saved records.

Extraction results depend on resume formatting and the quality of the document text. Scanned PDFs may require OCR support if their text is not extractable.

## Security and Privacy

- Keep `.env` out of version control.
- Never publish real database credentials or Flask secret keys.
- Do not commit private resumes or personally identifiable candidate information.
- Use `.gitignore` to exclude sensitive files and local virtual environments.
- Restrict access to the database and candidate information appropriately.

## Current Scope

This project focuses on resume parsing, candidate information extraction, PostgreSQL storage, and searchable candidate management.

The application is intended to run locally. Online hosting, organization-specific accounts, and multi-tenant access control are outside the current project scope.

## Future Enhancements

Potential improvements include:

- Improved extraction accuracy across different resume formats
- OCR support for scanned documents
- Job-description matching and candidate ranking
- Exporting candidate information to CSV or Excel
- Automated testing and additional input validation

## Author

**Karan Jaiswal**

GitHub:(https://github.com/KaranJaiswal-2603)

## License

No license has been specified yet. All rights are reserved by default unless a license is added to this repository.
