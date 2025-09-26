// frontend/src/App.js (FINAL VERSION with History and Translation Bonus)

import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE_URL = 'http://127.0.0.1:5000';
const API_PROCESS_URL = `${API_BASE_URL}/process-report`;
const API_REPORTS_URL = `${API_BASE_URL}/reports`;
const API_TRANSLATE_URL = `${API_BASE_URL}/translate`;

// --- Popup Component (remains the same) ---
const Popup = ({ message, type, onClose }) => {
  if (!message) return null;

  return (
    <div className={`popup popup-${type}`} onClick={onClose}>
      {message}
    </div>
  );
};


function App() {
  const [reportText, setReportText] = useState('');
  const [processedData, setProcessedData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [popupMessage, setPopupMessage] = useState(null);
  const [popupType, setPopupType] = useState('success');
  const [reportsHistory, setReportsHistory] = useState([]);
  const [translatedOutcome, setTranslatedOutcome] = useState({}); // {fr: "...", sw: "..."}
  const [activeTab, setActiveTab] = useState('process'); // 'process' or 'history'

  // Function to show the pop-up
  const showPopup = (message, type = 'success') => {
    setPopupMessage(message);
    setPopupType(type);
    setTimeout(() => setPopupMessage(null), 3000); 
  };
  
  // --- Bonus Feature: Fetch History ---
  const fetchHistory = async () => {
    try {
        const response = await fetch(API_REPORTS_URL);
        if (response.ok) {
            const data = await response.json();
            setReportsHistory(data);
            showPopup('History loaded successfully.', 'success');
        } else {
            showPopup('Failed to fetch report history.', 'error');
        }
    } catch (error) {
        showPopup('Network error while fetching history.', 'error');
    }
  };

  // Fetch history when the component mounts or when the tab changes to 'history'
  useEffect(() => {
    if (activeTab === 'history') {
        fetchHistory();
    }
  }, [activeTab]);


  // --- Core Feature: Process Report ---
  const handleProcessReport = async () => {
    if (!reportText.trim()) {
      showPopup('Please enter a medical report.', 'error');
      return;
    }

    setIsLoading(true);
    setProcessedData(null); 
    setTranslatedOutcome({}); // Clear previous translation

    try {
      const response = await fetch(API_PROCESS_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ report: reportText }),
      });

      const data = await response.json();

      if (response.ok) {
        setProcessedData(data);
        showPopup('Report processed successfully!', 'success');
      } else {
        showPopup(`Error processing report: ${data.error || 'Server error'}`, 'error');
      }
    } catch (error) {
      console.error('Fetch error:', error);
      showPopup('Network error. Check if the backend is running on port 5000.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // --- Bonus Feature: Translate Outcome ---
  const handleTranslate = async (lang) => {
    if (!processedData || !processedData.outcome) {
        showPopup('Process a report first to translate the outcome.', 'error');
        return;
    }

    try {
        const response = await fetch(API_TRANSLATE_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ outcome: processedData.outcome, language: lang }),
        });
        
        const data = await response.json();

        if (response.ok) {
            setTranslatedOutcome(prev => ({ ...prev, [lang]: data.translation }));
            showPopup(`Outcome translated to ${lang.toUpperCase()}.`, 'success');
        } else {
            showPopup(`Translation error: ${data.error}`, 'error');
        }
    } catch (error) {
        showPopup('Network error during translation.', 'error');
    }
  };

  // Renders the structured data table
  const renderResults = () => {
    if (!processedData) return null;

    const dataForDisplay = [
      { field: 'Drug Name', value: processedData.drug },
      { field: 'Adverse Events', value: (Array.isArray(processedData.adverse_events) ? processedData.adverse_events.join(', ') : processedData.adverse_events) || 'N/A' },
      { field: 'Severity', value: processedData.severity },
      { field: 'Outcome', value: processedData.outcome },
    ];

    return (
      <table className="results-table">
        <thead>
          <tr>
            <th>Field</th>
            <th>Extracted Value</th>
          </tr>
        </thead>
        <tbody>
          {dataForDisplay.map(({ field, value }) => (
            <tr key={field}>
              <td>{field}</td>
              <td>{value}</td>
            </tr>
          ))}
          {/* Translation Rows */}
          <tr className='translation-row'>
            <td>**French Translation**</td>
            <td>{translatedOutcome.fr || processedData.outcome}</td>
          </tr>
          <tr className='translation-row'>
            <td>**Swahili Translation**</td>
            <td>{translatedOutcome.sw || processedData.outcome}</td>
          </tr>
        </tbody>
      </table>
    );
  };
  
  // Renders the history table
  const renderHistory = () => {
    if (reportsHistory.length === 0) return <p style={{marginTop: '20px'}}>No reports found in history.</p>;

    return (
        <table className="results-table" style={{marginTop: '20px'}}>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Drug</th>
                    <th>Events</th>
                    <th>Severity</th>
                    <th>Outcome</th>
                    <th>Time</th>
                </tr>
            </thead>
            <tbody>
                {reportsHistory.map((report) => (
                    <tr key={report.id}>
                        <td>{report.id}</td>
                        <td>{report.drug}</td>
                        <td>{Array.isArray(report.adverse_events) ? report.adverse_events.join(', ') : report.adverse_events}</td>
                        <td>{report.severity}</td>
                        <td>{report.outcome}</td>
                        <td>{new Date(report.timestamp).toLocaleTimeString()}</td>
                    </tr>
                ))}
            </tbody>
        </table>
    );
  };


  return (
    <div className="App">
      <h1>Mini Regulatory Report Assistant 💊</h1>
      
      <Popup 
        message={popupMessage} 
        type={popupType} 
        onClose={() => setPopupMessage(null)}
      />

      {/* Tab Navigation */}
      <div className="tab-buttons" style={{marginBottom: '20px'}}>
        <button 
            className="process-button" 
            style={{marginRight: '10px', backgroundColor: activeTab === 'process' ? '#0077B6' : '#005691'}}
            onClick={() => setActiveTab('process')}
        >
            Process New Report
        </button>
        <button 
            className="process-button" 
            style={{backgroundColor: activeTab === 'history' ? '#0077B6' : '#005691'}}
            onClick={() => setActiveTab('history')}
        >
            View History ({reportsHistory.length})
        </button>
      </div>
      
      {/* Content based on Active Tab */}
      {activeTab === 'process' && (
        <>
            <div className="form-container">
                <h2>Enter Adverse Event Report</h2>
                <textarea
                placeholder="e.g., Patient experienced severe nausea and headache after taking Drug X. Patient recovered."
                value={reportText}
                onChange={(e) => setReportText(e.target.value)}
                />
                
                <button 
                className="process-button" 
                onClick={handleProcessReport} 
                disabled={isLoading}
                >
                {isLoading ? 'Processing...' : 'Process Report'}
                </button>
            </div>

            {processedData && (
                <>
                    <h2>Processing Results</h2>
                    {renderResults()}
                    
                    {/* Bonus: Translation Buttons */}
                    <div style={{marginTop: '20px'}}>
                        <button 
                            className="process-button" 
                            style={{marginRight: '10px'}}
                            onClick={() => handleTranslate('fr')}
                        >
                            Translate to French 🇫🇷
                        </button>
                        <button 
                            className="process-button" 
                            onClick={() => handleTranslate('sw')}
                        >
                            Translate to Swahili 🇰🇪
                        </button>
                    </div>
                </>
            )}
        </>
      )}

      {activeTab === 'history' && (
        <>
            <h2>Report History</h2>
            {renderHistory()}
        </>
      )}
    </div>
  );
}

export default App;