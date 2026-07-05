CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    skills TEXT,
    education TEXT,
    experience TEXT,
    certifications TEXT,
    match_score REAL,
    missing_skills TEXT
);