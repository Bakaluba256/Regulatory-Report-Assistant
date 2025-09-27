import json
import sqlite3
import spacy
from flask import Flask, request, jsonify
from flask_cors import CORS
import re

# --- DB Setup (Bonus 4a: SQLite) ---
DATABASE = 'reports.db'

def init_db():
    """Initializes the SQLite database table for reports."""
    # Ensure the database structure is created
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
CORS(app) 

try:
    # Load the pre-trained spaCy model
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Error loading spaCy model. Ensure you ran 'python -m spacy download en_core_web_sm'")
    exit()

# --- Core NLP Logic (Robust Extraction) ---
def extract_report_data(report_text):
    """
    Extracts structured data using robust spaCy Dependency Parsing and rule-based logic.
    """
    doc = nlp(report_text)
    
    drug = "Unknown Drug"
    adverse_events = []
    severity = "unknown"
    outcome = "unknown"

    # Keywords and constant lists
    SYMPTOM_VERBS = ["experienced", "had", "suffered", "felt", "develop", "get"]
    DRUG_VERBS = ["taking", "took", "given", "administered", "started", "gave"]
    SEVERITY_ADJS = ["severe", "critical", "life-threatening", "moderate", "serious", "mild", "slight", "painful", "bad"]
    OUTCOME_LEMMAS = ["recover", "resolve", "improve", "ongoing", "persist", "continue", "die", "better"]
    # Explicitly ignore non-symptoms, verbs, or outcome words
    IGNORE_AE = ["patient", "day", "week", "morning", "time", "moving", "improving", "better", "recovered", "improved", "medicine", "pill", "n/a", "then", "he", "she", "one"]
    
    
    # 1. Drug Extraction (Robust to Active and Passive Voice)
    drug_found = False
    for i, token in enumerate(doc):
        # Primary Check: PROPN following a DRUG_VERB lemma (Covers "taking Panadol" and "given Aspirin")
        if token.lemma_ in DRUG_VERBS:
            # Look at immediate children for PROPN (e.g., 'Panadol' is dobj of 'taking')
            drug_entity = next((child for child in token.children if child.pos_ == "PROPN" and child.dep_ in ["dobj", "attr", "pobj"]), None)
            if drug_entity:
                drug = ' '.join([t.text for t in drug_entity.subtree if t.pos_ in ["NOUN", "PROPN"] and t.text.lower() not in ["medicine", "pill"]])
                drug_found = True
                break
                
            # Secondary Check: Look at the next token (Covers "was given aspirin medicine")
            if i < len(doc) - 1 and doc[i+1].pos_ == "PROPN" and doc[i+1].text.lower() not in ["patient", "he", "she"]:
                drug = doc[i+1].text
                drug_found = True
                break
            
            # Tertiary Check: Handle passive voice where drug is subject of main clause verb, or object of a past participle.
            if token.lemma_ == "given":
                 if i > 0 and doc[i-1].pos_ == "PROPN" and doc[i-1].text.istitle() and doc[i-1].text.lower() not in ["patient"]:
                     drug = doc[i-1].text
                     drug_found = True
                     break
                     
        # Specific check for 'Drug X' type placeholders
        if token.text.lower() == 'drug' and i < len(doc) - 1 and doc[i+1].text.upper() == 'X':
            drug = "Drug X"
            drug_found = True
            break
            
    if drug_found and drug.lower() == 'medicine':
        drug = "Unknown Drug"

    
    # 2. Adverse Events & Severity Extraction (IMPROVED: Broader dependency search for symptoms)
    for sent in doc.sents:
        for token in sent:
            # Check for symptom verbs OR symptoms linked by 'was'/'is'
            if token.lemma_ in SYMPTOM_VERBS or (token.lemma_ == 'be' and token.dep_ == 'ROOT'):
                
                # Broadened targets: dobj, attr, conj, nsubj, or pobj/acomp if it's a NOUN/PROPN
                symptoms = [child for child in token.children if child.pos_ in ["NOUN", "PROPN"] and child.dep_ in ["dobj", "attr", "conj", "nsubj", "pobj", "acomp"]]
                
                # Check for gerund structure (e.g., 'after experiencing headache')
                if not symptoms and token.dep_ in ['pcomp', 'acl']:
                    symptoms.extend([child for child in token.children if child.pos_ in ["NOUN", "PROPN"] and child.dep_ in ["dobj", "attr", "conj"]])
                
                
                for symptom in symptoms:
                    symptom_text = symptom.text.lower().strip()
                    
                    # Filter: Only include if it is a NOUN/PROPN and not on the IGNORE_AE list
                    if symptom.pos_ in ["NOUN", "PROPN"] and symptom_text not in [w.lower() for w in IGNORE_AE]:
                        adverse_events.append(symptom_text)
                    
                        # Find Severity (Adjectives modifying the symptom)
                        for child in symptom.children:
                            if child.pos_ == "ADJ" and child.lemma_ in SEVERITY_ADJS:
                                severity = child.text.lower()
                                break
    
    # Final cleanup and filtering
    adverse_events = sorted(list(set(ae for ae in adverse_events)))
    adverse_events = [ae for ae in adverse_events if ae not in [w.lower() for w in OUTCOME_LEMMAS]]
    adverse_events = adverse_events if adverse_events else ["N/A"]
    
    
    # 3. Outcome Extraction
    for token in doc:
        if token.lemma_ in OUTCOME_LEMMAS:
            if token.lemma_ in ['better', 'improve']:
                 outcome = 'improved'
            elif token.lemma_ == 'recover':
                outcome = 'recovered'
            elif token.lemma_ == 'die':
                outcome = 'fatal'
            elif token.lemma_ in ['ongoing', 'continue', 'persist']:
                outcome = 'ongoing'
            break
            
    # Final severity check: if severity is unknown but an adjective is present and AE is found
    if severity == "unknown" and adverse_events != ["N/A"]:
        for adj in SEVERITY_ADJS:
            if adj in report_text.lower():
                severity = adj
                break
            
    return {
        "drug": drug.title() if drug != "Unknown Drug" else drug,
        "adverse_events": adverse_events,
        "severity": severity.title(),
        "outcome": outcome.title()
    }
    
# --- API Endpoint: POST /process-report (Part 1.1) ---
@app.route('/process-report', methods=['POST'])
def process_report():
    if not request.json or 'report' not in request.json:
        return jsonify({"error": "Missing 'report' field in request"}), 400

    report_text = request.json['report']
    
    try:
        processed_data = extract_report_data(report_text)
        # Save to DB (Bonus 4a)
        save_report(report_text, processed_data)
        return jsonify(processed_data), 200
    except Exception as e:
        app.logger.error(f"Processing error: {e}")
        return jsonify({"error": "Internal processing error"}), 500

# --- BONUS API Endpoint: GET /reports (Bonus 4b) ---
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

# --- BONUS API Endpoint: POST /translate (Bonus 4c) ---
TRANSLATION_DICT = {
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

    outcome = request.json['outcome'].title()
    language = request.json['language'].lower()

    if language not in ['fr', 'sw']:
         return jsonify({"error": "Language must be 'fr' (French) or 'sw' (Swahili)"}), 400

    translation = TRANSLATION_DICT.get(outcome, {}).get(language, "Translation N/A")
    
    return jsonify({"original": outcome, "language": language, "translation": translation}), 200


# Run the app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
