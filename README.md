# Personal Finance Tracker

A Python/Flask web app that lets you import CSV exports from your bank and investment accounts to track net worth, spending, and investment performance over time.

## Supported Institutions
- Chase (checking/credit)
- American Express
- Fidelity
- Coinbase
- Robinhood
- Marcus (Goldman Sachs)
- Charles Schwab

## Features
- **CSV Import** — Upload exports from any supported institution
- **Net Worth Tracking** — See your total net worth over time across all accounts
- **Spending Breakdown** — Categorize and visualize where your money goes
- **Investment Performance** — Track gains/losses across brokerage and crypto accounts
- **Duplicate Detection** — Re-uploading a file won't double-count transactions

## Tech Stack
- **Backend:** Python 3, Flask
- **Database:** SQLite
- **Frontend:** HTML, CSS, JavaScript, Chart.js
- **CSV Parsing:** Python csv module + custom parsers per institution

## Getting Started

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Git

### Installation
```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/finance-tracker.git
cd finance-tracker

# Create a virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Then open http://localhost:5000 in your browser.

## Project Structure
```
finance-tracker/
├── app.py                  # Flask application (main entry point)
├── requirements.txt        # Python dependencies
├── database/
│   └── models.py           # Database setup and helper functions
├── parsers/
│   ├── base.py             # Base parser (all parsers inherit from this)
│   ├── chase.py            # Chase CSV parser
│   ├── amex.py             # Amex CSV parser (TODO)
│   ├── fidelity.py         # Fidelity CSV parser (TODO)
│   ├── coinbase.py         # Coinbase CSV parser (TODO)
│   ├── robinhood.py        # Robinhood CSV parser (TODO)
│   ├── marcus.py           # Marcus CSV parser (TODO)
│   └── schwab.py           # Schwab CSV parser (TODO)
├── templates/              # HTML templates
│   ├── base.html           # Shared layout
│   ├── index.html          # Dashboard
│   └── upload.html         # CSV upload page
├── static/
│   ├── css/
│   │   └── style.css       # Styles
│   └── js/
│       └── charts.js       # Chart rendering
└── sample_data/            # Fake CSVs for testing (NEVER use real data here)
    └── chase_sample.csv
```

## Security Notes
- **NEVER commit real financial data to GitHub**
- The `.gitignore` file excludes the database and any uploaded files
- Sample/fake data is provided for testing and demo purposes
- This app runs locally only — your data stays on your machine

## Learning Roadmap
This project is built in phases. Each phase teaches new skills:

1. **Phase 1 — CSV Parsing:** Read and normalize bank exports (Python basics, file I/O)
2. **Phase 2 — Database:** Store transactions in SQLite (SQL basics, data modeling)
3. **Phase 3 — Web Interface:** Build upload + dashboard pages (Flask, HTML, CSS)
4. **Phase 4 — Visualizations:** Charts for net worth, spending, etc. (JavaScript, Chart.js)
5. **Phase 5 — Polish:** Error handling, duplicate detection, better categorization
