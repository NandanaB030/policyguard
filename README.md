# Policy Conflict & Staleness Detector

A lightweight, rule-based cybersecurity governance tool that parses policy documents (`.txt` and `.md`), extracts security obligations, categorizes them, and flags version conflicts, retention period contradictions, and stale content.

Built specifically as a beginner-friendly hackathon showcase. It does **not** rely on AI, machine learning, databases, or external APIs—using only Python standard libraries, Regex matching, Jaccard overlap, Flask, and ReportLab.

---

## 🛠️ Tech Stack
- **Backend:** Python 3.x, Flask (Development Server)
- **Document Engine:** ReportLab (Dynamic PDF generation)
- **Frontend Framework:** HTML5, CSS3, Vanilla JavaScript, Bootstrap 5 (Styling)
- **Data Visualization:** Chart.js (Interactive Pie & Bar charts)

---

## 🚀 Key Features

1. **Obligation Extraction:** Automatically identifies imperative lines containing modal verbs: `must`, `shall`, `should`, `required`, `prohibited`, and `must not`.
2. **Context-Aware Categorization:** Clusters policy statements into 9 primary compliance areas (Password, Encryption, Access Control, Data Retention, Logging, Network, Backup, MFA, and Others) using case-insensitive regex keyword matching.
3. **Conflict & Mismatch Engine:**
   - **Direct Conflicts:** Flags opposite commands targeting similar nouns in the same category (e.g., `MFA is required for admins` vs `MFA is prohibited for admins`) by comparing Jaccard similarity of token sets.
   - **Retention Mismatch:** Detects contradicting archival requirements (e.g., `backup retention must be 7 years` vs `backup retention shall be 3 years`) and normalizes units into days.
4. **Redundancy Finder:** Identifies identical or near-identical statements (similarity score > 85%) within or across policies.
5. **Staleness Auditor:**
   - **Review Age:** Analyzes metadata dates (e.g., `Last Reviewed: 2024-03-20`) relative to a baseline time of **July 12, 2026**. Flags policies reviewed over 18 months ago.
   - **Deprecated Tech:** Scans documents for outdated terms like `TLS 1.0`, `MD5`, `SHA-1`, `3DES`, or `Windows Server 2012`.
6. **Web Dashboard:** Visually lists total counts, health metrics, and issues inside a modern cybersecurity-themed interface.
7. **Report Compilation:** Downloads a structured PDF containing full conflict listings, stale files, duplicates, and overall compliance summaries.

---

## 📂 Project Structure

```text
├── app.py                     # Main Flask backend server and rule analysis engine
├── requirements.txt           # Python application dependencies
├── README.md                  # Setup and usage guide
├── templates/
│   └── index.html             # Dashboard frontend layout
├── static/
│   ├── css/
│   │   └── style.css          # Cyberpunk dark mode styling
│   └── js/
│       └── app.js             # Drag-and-drop uploads, API calls, Chart.js integrations
└── sample_policies/           # 10 preloaded policy files with intentional flaws
    ├── access_control_policy.txt
    ├── backup_and_recovery_policy.txt
    ├── data_retention_policy_corp.txt
    ├── data_retention_policy_vendor.txt
    ├── encryption_standards_legacy.txt
    ├── logging_audit_policy.txt
    ├── mfa_requirements.txt
    ├── network_security_policy.txt
    ├── password_policy_v1.txt
    └── password_policy_v2.txt
```

---

## ⚡ Quick Start

### 1. Install Dependencies
In your terminal, navigate to the project directory and run:
```bash
pip install -r requirements.txt
```

### 2. Start the Application
Run the Flask server:
```bash
python app.py
```

### 3. Open Dashboard
Open your web browser and navigate to:
```text
http://127.0.0.1:5000
```

---

## 🧪 Testing the Application
- On the dashboard landing page, click the **Load Samples** button. This automatically loads the 10 preset policies from the `sample_policies` folder.
- Inspect the statistics, look through the **Conflicts**, **Staleness**, **Redundancies**, and **All Obligations** tabs.
- Click **Download PDF Report** to view the ReportLab-generated compliance review document.
