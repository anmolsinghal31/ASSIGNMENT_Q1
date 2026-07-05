import os
import sqlite3
import logging
from flask import Flask, request, jsonify, Response
import pypdf
import docx2txt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Logging configuration setup to track data processes cleanly
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def init_db():
    conn = sqlite3.connect('project_data.db')
    cursor = conn.cursor()
    with open('schema.sql', 'r') as f:
        cursor.executescript(f.read())
    conn.commit()
    conn.close()

# Initialize the structural table on launch
init_db()

# --- NLP & EXTRACTION HELPERS ---

def extract_text(file_path):
    """Universal text parser handling PDF, DOCX, and TXT testing inputs."""
    text = ""
    try:
        if file_path.endswith('.pdf'):
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
        elif file_path.endswith('.docx'):
            text = docx2txt.process(file_path)
        elif file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
    except Exception as e:
        logging.error(f"Error reading file {file_path}: {str(e)}")
    return text

def parse_resume_details(text):
    """Scans and segments keywords dynamically to populate applicant criteria fields."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    name = lines[0] if lines else "Unknown"
    email = "Unknown"
    for line in lines:
        if "@" in line:
            email = line
            break

    # Targeted baseline keyword banks to align profiles
    skills_bank = ["python", "java", "javascript", "react", "sql", "aws", "docker", "flask", "html", "css"]
    edu_bank = ["btech", "b.tech", "mtech", "bca", "mca", "bsc", "bachelor", "master", "university"]
    cert_bank = ["aws certified", "pmp", "scrum", "google cloud", "udemy", "coursera"]

    text_lower = text.lower()
    
    found_skills = [s for s in skills_bank if s in text_lower]
    found_edu = [e for e in edu_bank if e in text_lower]
    found_certs = [c for c in cert_bank if c in text_lower]
    
    experience = "Entry Level"
    if "years" in text_lower or "experience" in text_lower or "developer" in text_lower:
        experience = "Mid-Senior Level"

    return {
        "name": name,
        "email": email,
        "skills": ", ".join(found_skills) if found_skills else "General Tech Skills",
        "education": ", ".join(found_edu) if found_edu else "Degree Details Not Clear",
        "experience": experience,
        "certifications": ", ".join(found_certs) if found_certs else "None Listed"
    }

# --- CONTROLLER ROUTE ENDPOINTS ---

@app.route('/upload', methods=['POST'])
def upload_resume():
    try:
        if 'file' not in request.files or 'job_description' not in request.form:
            return jsonify({"error": "Missing file or job_description"}), 400
            
        file = request.files['file']
        job_desc = request.form['job_description']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
            
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        
        extracted_text = extract_text(file_path)
        info = parse_resume_details(extracted_text)
        
        # Matrix vector comparison using TF-IDF token weighting blocks
        tfidf = TfidfVectorizer().fit_transform([extracted_text, job_desc])
        similarity = cosine_similarity(tfidf[0:1], tfidf[1:2])
        match_score = round(float(similarity[0][0]) * 100, 2)
        
        # Highlight gaps by isolating required skills absent in the resume content
        job_desc_lower = job_desc.lower()
        skills_bank = ["python", "java", "javascript", "react", "sql", "aws", "docker", "flask"]
        missing = [s for s in skills_bank if s in job_desc_lower and s not in info['skills'].lower()]
        missing_str = ", ".join(missing) if missing else "None"

        conn = sqlite3.connect('project_data.db')
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO candidates 
            (name, email, skills, education, experience, certifications, match_score, missing_skills) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (info['name'], info['email'], info['skills'], info['education'], info['experience'], info['certifications'], match_score, missing_str)
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "Success",
            "extracted_info": info,
            "match_score": f"{match_score}%",
            "missing_skills_highlighted": missing_str
        }), 200
    except Exception as e:
        logging.error(f"Upload error: {str(e)}")
        return jsonify({"error": "Internal processor error"}), 500

@app.route('/rankings', methods=['GET'])
def get_rankings():
    """Returns database matches ordered descending, supporting skill/experience query parameters."""
    try:
        skill_filter = request.args.get('skill', '')
        exp_filter = request.args.get('experience', '')
        edu_filter = request.args.get('education', '')

        conn = sqlite3.connect('project_data.db')
        cursor = conn.cursor()
        
        query = "SELECT * FROM candidates WHERE 1=1"
        params = []

        if skill_filter:
            query += " AND skills LIKE ?"
            params.append(f"%{skill_filter}%")
        if exp_filter:
            query += " AND experience LIKE ?"
            params.append(f"%{exp_filter}%")
        if edu_filter:
            query += " AND education LIKE ?"
            params.append(f"%{edu_filter}%")

        query += " ORDER BY match_score DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "skills": row[3],
                "education": row[4],
                "experience": row[5],
                "certifications": row[6],
                "match_score": f"{row[7]}%",
                "missing_skills": row[8]
            })
        return jsonify(results), 200
    except Exception as e:
        logging.error(f"Rankings error: {str(e)}")
        return jsonify({"error": "Could not read records"}), 500

@app.route('/export', methods=['GET'])
def export_candidates():
    try:
        conn = sqlite3.connect('project_data.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, match_score, skills FROM candidates ORDER BY match_score DESC")
        rows = cursor.fetchall()
        conn.close()

        csv_data = "ID,Name,Email,Match Score,Skills\n"
        for row in rows:
            csv_data += f"{row[0]},{row[1]},{row[2]},{row[3]}%,{row[4]}\n"

        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=candidates_report.csv"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)