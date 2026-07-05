import os
import sqlite3
import requests

url_upload = "http://127.0.0.1:5000/upload"
url_rankings = "http://127.0.0.1:5000/rankings"

# The target Job Description we are grading against
job_description = "KANAK JAIN kanak.jain@example.com SKILLS: Python, SQL, Flask, Docker, HTML, CSS EDUCATION: B.Tech in Computer Science EXPERIENCE: Worked as an AI Developer and Software Engineer."

print("\n" + "="*60)
print("STEP 1: CLEARING PREVIOUS TEST RECORDS FROM DATABASE")
print("="*60)

# Automatically connect to the database and wipe out old data from scratch
try:
    conn = sqlite3.connect('project_data.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM candidates;')
    conn.commit()
    conn.close()
    print("Database wiped clean! Processing current files from scratch...")
except Exception as e:
    print(f"Note: Database clean skipped or database busy: {str(e)}")

print("\n" + "="*60)
print("STEP 2: SCANNING AND UPLOADING ALL CURRENT RESUMES")
print("="*60)

# Get all files in the current folder that start with 'sample_resume'
current_directory = os.getcwd()
resume_files = [f for f in os.listdir(current_directory) if f.startswith("sample_resume") and f.endswith(".txt")]

if not resume_files:
    print("Error: No sample resume files found in the current directory!")
else:
    print(f"Found {len(resume_files)} resume file(s) to process: {resume_files}\n")
    
    for resume_filename in sorted(resume_files):
        file_path = os.path.join(current_directory, resume_filename)
        try:
            with open(file_path, "rb") as f:
                print(f"Sending {resume_filename} to the backend...")
                response = requests.post(
                    url_upload, 
                    files={"file": (resume_filename, f, "text/plain")}, 
                    data={"job_description": job_description}
                )
                if response.status_code == 200:
                    print(f"Successfully processed {resume_filename}!")
                else:
                    print(f"Error uploading {resume_filename}: {response.text}")
        except Exception as e:
            print(f"Failed to read {resume_filename}: {str(e)}")

print("\n" + "="*60)
print("STEP 3: FETCHING LIVE LEADERBOARD RANKINGS VIA /rankings")
print("="*60)

# Fetch sorted rankings from the database
try:
    response = requests.get(url_rankings)
    if response.status_code == 200:
        candidates = response.json()
        for idx, candidate in enumerate(candidates, start=1):
            print(f"RANK #{idx}")
            print(f"Candidate Name : {candidate.get('name')}")
            print(f"Email Address  : {candidate.get('email')}")
            print(f"Skills Held    : {candidate.get('skills')}")
            print(f"Missing Skills : {candidate.get('missing_skills')}")
            print(f"MATCH SCORE    : {candidate.get('match_score')}")
            print("-" * 40)
    else:
        print("Error fetching rankings from server:", response.text)
except requests.exceptions.ConnectionError:
    print("Connection Error: Is your app.py backend server running on port 5000?")

print("="*60 + "\n")