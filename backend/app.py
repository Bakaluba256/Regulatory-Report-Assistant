import json
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re

# --- DB Setup (Bonus 4a: SQLite) ---
DATABASE = 'reports.db'

def init_db():
    """Initializes the SQLite database table for reports."""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_report TEXT NOT NULL,
                drug TEXT,
                adverse_events TEXT, -- Stored as JSON string
                severity TEXT,
                outcome TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

def save_report(raw_report, data):
    """Saves the processed report data to the SQLite database."""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO reports (raw_report, drug, adverse_events, severity, outcome) VALUES (?, ?, ?, ?, ?)",
            (
                raw_report, 
                data['drug'], 
                json.dumps(data['adverse_events']),
                data['severity'], 
                data['outcome']
            )
        )
        conn.commit()

# Initialize the database on startup
init_db()


# --- Flask & Initialization ---
app = Flask(__name__)

# Configure CORS dynamically for deployment (Render, Vercel, etc.)
# FALLBACK: Use local URL for development (http://localhost:3000)
ALLOWED_ORIGIN = os.environ.get('REACT_FRONTEND_URL', 'http://localhost:3000')

# Handle multiple origins if environment variable is comma-separated
if ',' in ALLOWED_ORIGIN:
    origins_list = ALLOWED_ORIGIN.split(',')
else:
    # Always allow the deployed URL and localhost for testing
    origins_list = [ALLOWED_ORIGIN, 'http://localhost:3000'] 

# Initialize CORS with the dynamic list of allowed origins
CORS(app, resources={r"/*": {"origins": origins_list}})


# --- Core Extraction Logic (PURE RULE-BASED) ---

# Expanded lists for more accurate rule-based matching
DRUG_PATTERNS = r'(?:taking|took|given|administered|started|gave)\s+([A-Z]\w+)\s*(?:[A-Z]\w*)*|Drug\s+[A-Z]'
SYMPTOMS_LIST = [
    "nausea", "headache", "vomiting", "fever", "rash", "dizziness", "vertigo", 
    "fatigue", "diarrhea", "pain", "swelling", "bleeding", "seizure", "insomnia", 
    "difficulty breathing", "stomach ache", "cramps"
]
SEVERITY_KEYWORDS = {
    "severe": ["severe", "critical", "life-threatening", "serious"],
    "moderate": ["moderate", "significant"],
    "mild": ["mild", "slight", "minimal", "low"]
}
OUTCOME_KEYWORDS = {
    "recovered": ["recovered", "resolved", "improved", "better"],
    "ongoing": ["ongoing", "persisting", "continuing"],
    "fatal": ["fatal", "died", "death"]
}


def extract_report_data(report_text):
    """
    Extracts structured data using only REGEX and simple keyword matching.
    """
    report_lower = report_text.lower()
    
    drug = "Unknown Drug"
    adverse_events = []
    severity = "unknown"
    outcome = "unknown"
    
    # 1. Drug Extraction (REGEX)
    
    # Check for 'Drug X' pattern
    drug_match_x = re.search(r'Drug\s+([A-Z])', report_text)
    if drug_match_x:
        drug = f"Drug {drug_match_x.group(1)}"
    else:
        # Look for a capitalized word following key drug verbs (e.g., 'taking Panadol', 'given Aspirin')
        drug_match_cap = re.search(r'(?:taking|took|given|administered|started|gave)\s+([A-Z]\w+)\s*(?:[A-Z]\w*)*', report_text)
        if drug_match_cap:
            drug = drug_match_cap.group(1)
        
        # Fallback: Look for capitalized word preceded by 'was given' (crude passive voice check)
        elif 'was given' in report_lower:
            # Look for an uppercase word immediately following 'was given'
            passive_match = re.search(r'was\s+given\s+([A-Z]\w+)', report_text)
            if passive_match:
                drug = passive_match.group(1)

    # 2. Adverse Events (Keyword Matching)
    adverse_events = sorted(list(set(
        symptom for symptom in SYMPTOMS_LIST 
        if symptom in report_lower
    )))
    adverse_events = adverse_events if adverse_events else ["N/A"]
    
    # 3. Severity Extraction (Keyword Matching)
    for level, keywords in SEVERITY_KEYWORDS.items():
        if any(kw in report_lower for kw in keywords):
            severity = level
            break

    # 4. Outcome Extraction (Keyword Matching)
    for level, keywords in OUTCOME_KEYWORDS.items():
        if any(kw in report_lower for kw in keywords):
            outcome = level
            break
            
    # Final formatting
    return {
        "drug": drug.title() if drug != "Unknown Drug" and not drug.isupper() else drug,
        "adverse_events": adverse_events,
        "severity": severity.title(),
        "outcome": outcome.title()
    }
    
# --- API Endpoint: POST /process-report ---
@app.route('/process-report', methods=['POST'])
def process_report():
    if not request.json or 'report' not in request.json:
        return jsonify({"error": "Missing 'report' field in request"}), 400

    report_text = request.json['report']
    
    try:
        processed_data = extract_report_data(report_text)
        save_report(report_text, processed_data)
        return jsonify(processed_data), 200
    except Exception as e:
        app.logger.error(f"Processing error: {e}")
        return jsonify({"error": "Internal processing error"}), 500

# --- BONUS API Endpoint: GET /reports (History) ---
@app.route('/reports', methods=['GET'])
def get_reports():
    """Fetches all past reports from the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("SELECT id, raw_report, drug, adverse_events, severity, outcome, timestamp FROM reports ORDER BY timestamp DESC")
    reports = cursor.fetchall()
    conn.close()

    reports_list = []
    for report in reports:
        report_dict = dict(report)
        # Deserialize JSON string back to list for adverse_events
        try:
             report_dict['adverse_events'] = json.loads(report_dict['adverse_events'])
        except (json.JSONDecodeError, TypeError):
             report_dict['adverse_events'] = ["N/A"]
             
        reports_list.append(report_dict)

    return jsonify(reports_list), 200

# --- BONUS API Endpoint: POST /translate ---
TRANSLATION_DICT = {
    "Recovered": {"fr": "Récupéré", "sw": "Amepona"},
    "Improved": {"fr": "Amélioré", "sw": "Kupata nafuu"},
    "Ongoing": {"fr": "En cours", "sw": "Inaendelea"},
    "Fatal": {"fr": "Fatal", "sw": "Mbaya"},
    "Unknown": {"fr": "Inconnu", "sw": "Haijulikani"},
    "Severe": {"fr": "Grave", "sw": "Kali"},
    "Mild": {"fr": "Léger", "sw": "Kidogo"},
    "Moderate": {"fr": "Modéré", "sw": "Wastani"},
}

@app.route('/translate', methods=['POST'])
def translate_outcome():
    """Translates the outcome (or severity) into French or Swahili."""
    if not request.json or 'outcome' not in request.json or 'language' not in request.json:
        return jsonify({"error": "Missing 'outcome' or 'language' field in request"}), 400

    outcome = request.json['outcome'].title()
    language = request.json['language'].lower()

    if language not in ['fr', 'sw']:
         return jsonify({"error": "Language must be 'fr' (French) or 'sw' (Swahili)"}), 400

    translation = TRANSLATION_DICT.get(outcome, {}).get(language, "Translation N/A")
    
    return jsonify({"original": outcome, "language": language, "translation": translation}), 200


# Run the app
if __name__ == '__main__':
    # Use host='0.0.0.0' for deployment/docker compatibility
    app.run(debug=True, host='0.0.0.0', port=5000)