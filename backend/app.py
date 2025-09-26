# backend/app.py (Final Version with DB, Smart NLP Debugged, and Translation Bonus)

import json
import sqlite3
import spacy
import re
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- DB Setup ---
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


# --- Flask & NLP Initialization ---
app = Flask(__name__)
# Enable CORS for frontend communication
CORS(app) 

try:
    # Load the pre-trained spaCy model
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Error loading spaCy model. Ensure you ran 'python -m spacy download en_core_web_sm'")
    exit()

# --- Smarter NLP and Dependency-Based Processing Logic (DEBUGGED) ---
def extract_report_data(report_text):
    """
    Extracts structured data using spaCy Dependency Parsing and linguistic rules.
    """
    doc = nlp(report_text)
    
    drug = "Unknown Drug"
    adverse_events = []
    severity = "unknown"
    outcome = "unknown"

    SYMPTOM_VERBS = ["experienced", "had", "suffered", "felt", "was", "is", "develop", "get"]
    DRUG_VERBS = ["taking", "took", "given", "administered", "started", "stop", "gave"] # Added 'gave'
    SEVERITY_ADJS = ["severe", "critical", "life-threatening", "moderate", "serious", "mild", "slight", "painful", "bad"] # Added 'painful', 'bad'
    OUTCOME_LEMMAS = ["recover", "resolve", "improve", "ongoing", "persist", "continue", "die", "better"] # Added 'better'

    
    # 1. Drug Extraction (Using broader dependency and immediate neighbors)
    for token in doc:
        # 1a. Check for drug-related verbs (e.g., 'given aspirin medicine')
        if token.lemma_ in DRUG_VERBS:
            # Look for the direct object (dobj) or object of a preposition (pobj)
            drug_entity = next((child for child in token.children if child.dep_ in ["dobj", "pobj"]), None)
            if drug_entity:
                # Capture the text of the noun/entity that is the drug
                drug_token = drug_entity
                # Capture compound names (like 'aspirin medicine') by checking neighbors
                if drug_token.dep_ == 'compound' and drug_token.head:
                    drug = ' '.join([t.text for t in drug_token.subtree])
                else:
                    drug = drug_token.text
                break
        
        # 1b. Fallback: Search for capitalized words near "medicine" or "drug"
        if token.text.lower() in ["medicine", "drug"] and token.head.text.istitle():
            drug = token.head.text
            break

    # 2. Adverse Events & Severity Extraction
    for sent in doc.sents:
        for token in sent:
            if token.lemma_ in SYMPTOM_VERBS:
                # Find nouns/symptoms related to the verb (dobj, attr, or conjunctions)
                symptoms = [child for child in token.children if child.pos_ == "NOUN" or child.dep_ in ["dobj", "attr", "conj"]]
                
                for symptom in symptoms:
                    if symptom.text.lower() not in ["patient", "day", "week", "morning", "time", "moving"]:
                        adverse_events.append(symptom.text)
                    
                    # Find Severity (Adjectives modifying the symptom)
                    for child in symptom.children:
                        if child.pos_ == "ADJ" and child.lemma_ in SEVERITY_ADJS:
                            severity = child.text.lower()
                            break 
    
    # Clean up and ensure unique events (remove duplicates and generic words)
    adverse_events = sorted(list(set(ae.lower().strip() for ae in adverse_events)))
    # If adverse_events is empty after cleaning, set to N/A
    adverse_events = adverse_events if adverse_events else ["N/A"]
    
    
    # 3. Outcome Extraction (Looking for specific verbs/lemmas)
    for token in doc:
        if token.lemma_ in OUTCOME_LEMMAS:
            if token.lemma_ == 'better' or token.lemma_ == 'improve':
                 outcome = 'improved'
            elif token.lemma_ == 'recover':
                outcome = 'recovered'
            elif token.lemma_ == 'die':
                outcome = 'fatal'
            elif token.lemma_ == 'ongoing':
                outcome = 'ongoing'
            # Stop after the first one is found
            break

    return {
        "drug": drug.title() if drug not in ["Unknown Drug", "aspirin medicine"] else drug,
        "adverse_events": adverse_events,
        "severity": severity,
        "outcome": outcome.title() # Title case for display
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
        return jsonify({"error": "Internal processing error", "details": str(e) if app.debug else "See server logs"}), 500

# --- BONUS API Endpoint: GET /reports ---
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
        report_dict['adverse_events'] = json.loads(report_dict['adverse_events'])
        reports_list.append(report_dict)

    return jsonify(reports_list), 200

# --- BONUS API Endpoint: POST /translate ---
# This fulfills the requirement to add translation support [cite: 28, 29]
TRANSLATION_DICT = {
    # French
    "Recovered": {"fr": "Récupéré", "sw": "Amepona"},
    "Improved": {"fr": "Amélioré", "sw": "Kupata nafuu"},
    "Ongoing": {"fr": "En cours", "sw": "Inaendelea"},
    "Fatal": {"fr": "Fatal", "sw": "Mbaya"},
    "Unknown": {"fr": "Inconnu", "sw": "Haijulikani"},
}

@app.route('/translate', methods=['POST'])
def translate_outcome():
    """Translates the outcome into French or Swahili."""
    if not request.json or 'outcome' not in request.json or 'language' not in request.json:
        return jsonify({"error": "Missing 'outcome' or 'language' field in request"}), 400

    outcome = request.json['outcome'].title() # Ensure first letter is capitalized for lookup
    language = request.json['language'].lower() # 'fr' or 'sw'

    if language not in ['fr', 'sw']:
         return jsonify({"error": "Language must be 'fr' (French) or 'sw' (Swahili)"}), 400

    translation = TRANSLATION_DICT.get(outcome, {}).get(language, "Translation N/A")
    
    return jsonify({"original": outcome, "language": language, "translation": translation}), 200


# Run the app
if __name__ == '__main__':
    app.run(debug=True, port=5000)