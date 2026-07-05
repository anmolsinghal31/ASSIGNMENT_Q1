Resume Screening System
1. Setup
Install the necessary dependencies:

Bash
pip install flask scikit-learn pypdf docx2txt requests
2. Run Application
Start the backend server:

Bash
python app.py
3. Run Test Suite
In a new terminal, execute the automated screening tests:

Bash
python run_test.py
4. API Endpoints
POST /upload: Submit resume and job description.

GET /rankings: Retrieve ranked candidate leaderboard.

GET /export: Download candidate report as CSV.