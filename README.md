# Finance Tracker

A local-first Flask app for importing bank CSVs, reviewing transactions, creating categorization rules, and tracking monthly budgets.

![Finance Tracker Demo](docs/finance-tracker-demo-2026-04-26.gif)

## Highlights

- **Private CSV import**: Files are parsed locally and are not sent to an external service.
- **Known bank parsers + generic mapping**: Chase checking/credit are registered today, and the generic CSV wizard lets you map date, description, amount, category, and account type columns for other exports.
- **Dashboard widgets**: Summary stats, balance charts, recent activity, accounts, budget snapshot, alerts, and quick actions in a customizable layout.
- **Transaction review workflow**: Mark transactions reviewed, edit categories inline, and add/edit/delete manual transactions.
- **Rules engine**: Create rules that match descriptions or amounts, rename transactions, set categories, preview matching transactions live, apply rules retroactively, and reorder rule priority.
- **Budget tracking**: Set monthly category budgets, filter/sort budget cards, edit limits inline, view pacing, and auto-create suggested budgets from spending averages.
- **Sample data**: Load bundled fake transactions and starter budgets from the empty dashboard.
- **Themes and branding**: Multiple themes, favicon assets, and the Four Beads logo system.
- **CSV export**: Download all tracked transactions from `/export.csv`.

## Getting Started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open [http://localhost:5000](http://localhost:5000).

## Using The App

1. Open **Upload** and import a CSV, or use **Try with sample data** from the empty dashboard.
2. Review the dashboard and mark transactions as reviewed.
3. Create rules on **Rules** to automate recurring categorization.
4. Set category limits on **Budget** and monitor monthly progress.
5. Export transactions from `/export.csv` when you need a spreadsheet copy.

## CSV Import

Registered parsers:

- Chase checking
- Chase credit

For other banks or brokerages, choose **Other / Generic CSV** and map the required columns manually. The app supports optional category columns and sign flipping for credit-card style exports where purchases are positive.

## Project Structure

```text
finance-tracker/
├── app.py                  # Flask routes, upload flow, APIs
├── database/
│   └── models.py           # SQLite schema and query helpers
├── parsers/                # Institution-specific CSV parsers
├── sample_data/            # Fake CSVs for demos and testing
├── static/
│   ├── css/                # App styles and themes
│   ├── img/                # Logo and illustration assets
│   └── js/                 # Chart helpers
└── templates/              # Flask/Jinja page templates
```

## Security Notes

- Do not commit real financial data.
- `finance.db` and uploaded files should stay local.
- Use the bundled sample data for demos, tests, and screenshots.
