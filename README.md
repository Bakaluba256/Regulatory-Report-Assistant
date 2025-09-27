# Mini Regulatory Report Assistant (Full-Stack AI Project Intern Assignment)

Based on the provided assignment brief and the implemented Python (Flask) backend and React frontend code, here is a concise and structured `README.md` file.

````markdown

This project implements a **Mini Regulatory Report Assistant** as a full-stack application, simulating a small slice of the workflow for processing adverse event reports as outlined in the take-home assignment.

The application is built with a **Python/Flask** backend for data extraction and persistence, and a **React.js** frontend for the user interface.

## Features

The application fulfills all core requirements and includes the following:

### Core Features
* **POST /process-report API:** Accepts a raw adverse event report and uses **rule-based logic** (pure Regex and keyword matching) to extract structured data.
    * **Extracted Fields:** `drug`, `adverse_events`, `severity`, `outcome`.
* **Functional Frontend (React):**
    * Input form to paste or type a medical report.
    * Button to submit and process the report.
    * Display of the structured data results in a clear table format.

### Bonus Features
* **Database Persistence:** Processed reports are saved to a simple **SQLite database (`reports.db`)**.
* **Reports History :**
    * **GET /reports API:** Fetches all past processed reports.
    * **Frontend History Tab:** Allows users to view a list of all historical reports fetched from the backend.
* **Multilingual Translation :**
    * **POST /translate API:** Translates the extracted **Outcome** into French (`fr`) or Swahili (`sw`) using a dictionary lookup.
    * **Frontend Translation Buttons:** Buttons to trigger the translation and display the results inline with the main table.


## Setup and Installation

Follow these steps to set up and run the application locally.

### 1. Prerequisites

Ensure you have the following installed:
* **Python 3.8+** (for the backend)
* **Node.js & npm/yarn** (for the frontend)

### 2. Backend Setup (Python/Flask)

1.  Navigate into the `/backend` directory (assuming a standard project structure).
2.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: The `requirements.txt` file should contain `Flask`, `flask-cors`, and any other necessary libraries like `json` and `sqlite3` which are built-in)*.
4.  Run the Flask server:
    ```bash
    python app.py
    ```
    The backend API will run on `http://127.0.0.1:5000`.

### 3. Frontend Setup (React)

1.  Navigate into the `/frontend` directory (assuming a standard project structure).
2.  Install the React dependencies:
    ```bash
    npm install
    # OR
    yarn install
    ```
3.  Start the React development server:
    ```bash
    npm start
    # OR
    yarn start
    ```
    The frontend application will open in your browser, typically at `http://localhost:3000`.

***

##  API Endpoints

| Method | Endpoint | Description | Input/Output Example |
| :--- | :--- | :--- | :--- |
| `POST` | `/process-report` | Extracts structured data from a raw report and saves it to the DB. | **Input:** `{"report": "..."}` **Output:** `{"drug": "...", "severity": "..."}` |
| `GET` | `/reports` | Fetches the full history of all processed reports from the SQLite DB. | **Output:** `[{"id": 1, "drug": "...", "timestamp": "..."}]` |
| `POST` | `/translate` | Translates a given outcome (or severity) to French or Swahili. | **Input:** `{"outcome": "Recovered", "language": "fr"}` **Output:** `{"translation": "Récupéré"}` |


##  Project Structure

├── backend/
│   ├── app.py           \# Flask application with API endpoints and logic
│   ├── requirements.txt
│   └── reports.db       \# SQLite database file (created on first run)
├── frontend/
│   ├── src/
│   │   └── App.js       \# Main React component logic and UI
│   ├── public/
│   ├── package.json
│   └── ...
├── README.md            \# This file
