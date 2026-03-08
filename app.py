"""
Personal Finance Tracker — Main Application

This is the entry point for your Flask web app.
Run it with: python app.py
Then open http://localhost:5000 in your browser.

WHAT YOU'LL LEARN HERE:
- How Flask routes work (URLs → Python functions)
- How to handle file uploads
- How to pass data from Python to HTML templates
"""

import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from database.models import initialize_database, add_account, add_transactions, get_all_transactions, get_all_accounts
from parsers import get_parser, PARSERS

# ---- APP SETUP ----
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-fallback-key-change-in-production')

# Create an uploads folder to temporarily store CSV files
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---- ROUTES ----
# Each route is a URL that your app responds to

@app.route('/')
def index():
    """
    Dashboard page — shows summary of your finances.
    This is what you see when you go to http://localhost:5000/
    """
    accounts = get_all_accounts()
    transactions = get_all_transactions()

    # Calculate some basic stats to show on the dashboard
    total_transactions = len(transactions)

    # Sum up spending (negative amounts) and income (positive amounts)
    total_spent = sum(t['amount'] for t in transactions if t['amount'] < 0)
    total_income = sum(t['amount'] for t in transactions if t['amount'] > 0)

    return render_template('index.html',
                           accounts=accounts,
                           transactions=transactions,
                           total_transactions=total_transactions,
                           total_spent=total_spent,
                           total_income=total_income)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """
    CSV upload page.
    GET = show the upload form
    POST = process the uploaded file
    """
    if request.method == 'POST':
        # ---- Handle the file upload ----

        # Check if a file was actually submitted
        if 'csv_file' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('upload'))

        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('upload'))

        # Get which parser to use (from the dropdown)
        parser_key = request.form.get('institution')
        parser = get_parser(parser_key)

        if not parser:
            flash(f'Unknown institution: {parser_key}', 'error')
            return redirect(url_for('upload'))

        # Read the CSV file contents
        csv_text = file.read().decode('utf-8')

        # Parse the CSV into standardized transactions
        try:
            transactions = parser.parse(csv_text)
        except Exception as e:
            flash(f'Error parsing CSV: {str(e)}', 'error')
            return redirect(url_for('upload'))

        if not transactions:
            flash('No transactions found in file', 'error')
            return redirect(url_for('upload'))

        # Create or find the account
        # For now, we'll create a new account each time
        # TODO: Add logic to find existing account or let user select one
        account_name = request.form.get('account_name', f'{parser.institution_name} account')
        account_id = add_account(account_name, parser.institution_name, parser.account_type)

        # Save transactions to database
        count = add_transactions(transactions, account_id, file.filename)

        flash(f'Successfully imported {count} transactions from {file.filename}!', 'success')
        return redirect(url_for('index'))

    # GET request — show the upload form
    available_parsers = list(PARSERS.keys())
    return render_template('upload.html', parsers=available_parsers)


@app.route('/api/transactions')
def api_transactions():
    """
    API endpoint that returns transactions as JSON.
    This is used by the JavaScript charts on the dashboard.

    YOUR TASK (Phase 4): Add more API endpoints for:
    - /api/spending-by-category — grouped spending data for pie chart
    - /api/net-worth-over-time — balance data for line chart
    """
    transactions = get_all_transactions()
    # Convert Row objects to regular dicts for JSON serialization
    return jsonify([dict(t) for t in transactions])


# ---- START THE APP ----
if __name__ == '__main__':
    # Initialize the database (creates tables if they don't exist)
    initialize_database()

    # Start the Flask development server
    # debug=True means it auto-restarts when you change code
    print("\n🚀 Finance Tracker is running!")
    print("   Open http://localhost:5000 in your browser\n")
    app.run(debug=True, port=5000)
