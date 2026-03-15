"""
Personal Finance Tracker — Main Application

Features:
- CSV import with column-mapping wizard
- Dashboard with charts and transaction timeline
- Rules engine for auto-categorization
- Transaction review workflow (checkmark system)
- Budget page with category spending limits
- API endpoints for charts
"""

import os
import csv
from io import StringIO
from datetime import datetime
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, jsonify, session)
from database.models import (
    initialize_database, add_account, add_transactions,
    get_all_transactions, get_all_accounts, get_all_categories,
    update_transaction_review, update_transaction_category, get_review_stats,
    create_transaction, delete_transaction, update_transaction,
    add_rule, get_all_rules, delete_rule, toggle_rule, apply_rules_retroactively,
    set_budget, get_budgets, delete_budget, get_spending_by_category_for_month,
    get_avg_spending_by_category, get_monthly_spending_history
)
from parsers import get_parser, PARSERS

# ---- APP SETUP ----
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-fallback-key-change-in-production')

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ==============================================================
# DASHBOARD
# ==============================================================

@app.route('/')
def index():
    """Landing / get-started page."""
    return render_template('landing.html')


@app.route('/dashboard')
def dashboard():
    accounts = get_all_accounts()
    transactions = get_all_transactions()
    review_stats = get_review_stats()

    total_transactions = len(transactions)
    total_spent = sum(t['amount'] for t in transactions if t['amount'] < 0)
    total_income = sum(t['amount'] for t in transactions if t['amount'] > 0)

    return render_template('index.html',
                           accounts=accounts,
                           transactions=transactions,
                           total_transactions=total_transactions,
                           total_spent=total_spent,
                           total_income=total_income,
                           review_stats=review_stats)


# ==============================================================
# CSV UPLOAD — Now with column-mapping wizard
# ==============================================================

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """
    Two-step CSV upload:
    Step 1 (GET or POST without 'confirm'): Show the upload form or preview
    Step 2 (POST with 'confirm'): Actually import the data
    """
    if request.method == 'POST':
        # ---- STEP 2: Confirm and import ----
        if request.form.get('confirm') == '1':
            return _handle_csv_import()

        # ---- STEP 1: Parse and show preview ----
        return _handle_csv_preview()

    # GET — show upload form
    available_parsers = list(PARSERS.keys())
    return render_template('upload.html', parsers=available_parsers, step='upload')


def _handle_csv_preview():
    """Parse the uploaded CSV and show a preview with column mapping."""
    if 'csv_file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('upload'))

    file = request.files['csv_file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('upload'))

    csv_text = file.read().decode('utf-8-sig')  # utf-8-sig handles BOM
    institution = request.form.get('institution')
    account_name = request.form.get('account_name', 'My Account')

    # If using a known parser, parse normally and show preview
    if institution and institution != 'generic_csv':
        parser = get_parser(institution)
        if parser:
            try:
                transactions = parser.parse(csv_text)
                # Store in session for step 2
                session['pending_csv'] = csv_text
                session['pending_institution'] = institution
                session['pending_account_name'] = account_name
                session['pending_filename'] = file.filename

                return render_template('upload.html',
                                       step='preview',
                                       transactions=transactions[:15],
                                       total_count=len(transactions),
                                       filename=file.filename,
                                       institution=institution,
                                       account_name=account_name,
                                       parsers=list(PARSERS.keys()))
            except Exception as e:
                flash(f'Error parsing CSV: {str(e)}', 'error')
                return redirect(url_for('upload'))

    # Generic CSV — show column mapping wizard
    reader = csv.DictReader(StringIO(csv_text))
    headers = reader.fieldnames or []
    rows = []
    for i, row in enumerate(reader):
        if i >= 5:
            break
        rows.append(dict(row))

    session['pending_csv'] = csv_text
    session['pending_account_name'] = account_name
    session['pending_filename'] = file.filename

    return render_template('upload.html',
                           step='map_columns',
                           headers=headers,
                           sample_rows=rows,
                           filename=file.filename,
                           account_name=account_name,
                           parsers=list(PARSERS.keys()))


def _handle_csv_import():
    """Confirm and import transactions from session data."""
    csv_text = session.get('pending_csv')
    institution = session.get('pending_institution', '')
    account_name = session.get('pending_account_name', 'My Account')
    filename = session.get('pending_filename', 'upload.csv')

    if not csv_text:
        flash('No pending upload found. Please try again.', 'error')
        return redirect(url_for('upload'))

    # Check if using column mapping (generic CSV)
    date_col = request.form.get('col_date')
    desc_col = request.form.get('col_description')
    amount_col = request.form.get('col_amount')

    if date_col and desc_col and amount_col:
        # Generic CSV with user-mapped columns
        transactions = _parse_generic_csv(csv_text, date_col, desc_col, amount_col,
                                           request.form.get('col_category'),
                                           request.form.get('amount_flip') == '1')
        inst_name = 'generic'
        acct_type = request.form.get('account_type', 'checking')
    else:
        # Known institution parser
        parser = get_parser(institution)
        if not parser:
            flash('Unknown institution', 'error')
            return redirect(url_for('upload'))
        transactions = parser.parse(csv_text)
        inst_name = parser.institution_name
        acct_type = parser.account_type

    if not transactions:
        flash('No transactions found in file', 'error')
        return redirect(url_for('upload'))

    account_id = add_account(account_name, inst_name, acct_type)
    count, skipped = add_transactions(transactions, account_id, filename)

    # Clear session data
    session.pop('pending_csv', None)
    session.pop('pending_institution', None)
    session.pop('pending_account_name', None)
    session.pop('pending_filename', None)

    msg = f'Successfully imported {count} transactions from {filename}!'
    if skipped > 0:
        msg += f' ({skipped} duplicates skipped)'
    flash(msg, 'success')
    return redirect(url_for('dashboard'))


def _parse_generic_csv(csv_text, date_col, desc_col, amount_col,
                        category_col=None, flip_amount=False):
    """Parse a generic CSV using user-specified column mapping."""
    reader = csv.DictReader(StringIO(csv_text))
    transactions = []

    date_formats = ['%m/%d/%Y', '%Y-%m-%d', '%m/%d/%y', '%m-%d-%Y',
                    '%d/%m/%Y', '%Y/%m/%d']

    for row in reader:
        if not row.get(date_col) or not row.get(amount_col):
            continue

        # Try multiple date formats
        date_str = row[date_col].strip()
        parsed_date = None
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
                break
            except ValueError:
                continue

        if not parsed_date:
            continue

        try:
            amount = float(row[amount_col].replace(',', '').replace('$', ''))
        except (ValueError, TypeError):
            continue

        if flip_amount:
            amount = -amount

        transaction = {
            'date': parsed_date,
            'description': row.get(desc_col, '').strip(),
            'amount': amount,
            'category': row.get(category_col, 'Uncategorized').strip() if category_col else 'Uncategorized'
        }
        transactions.append(transaction)

    return transactions


# ==============================================================
# RULES ENGINE PAGE
# ==============================================================

@app.route('/rules', methods=['GET', 'POST'])
def rules():
    """Rules page — create, view, and manage auto-categorization rules."""
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            add_rule(
                name=request.form.get('name', 'New Rule'),
                condition_field=request.form.get('condition_field', 'description'),
                condition_op=request.form.get('condition_op', 'contains'),
                condition_value=request.form.get('condition_value', ''),
                action_category=request.form.get('action_category') or None,
                action_rename=request.form.get('action_rename') or None
            )
            flash('Rule created!', 'success')

        elif action == 'delete':
            delete_rule(int(request.form.get('rule_id')))
            flash('Rule deleted', 'success')

        elif action == 'toggle':
            toggle_rule(int(request.form.get('rule_id')))
            flash('Rule toggled', 'success')

        elif action == 'apply_all':
            updated = apply_rules_retroactively()
            flash(f'Rules applied! {updated} transactions updated.', 'success')

        return redirect(url_for('rules'))

    all_rules = get_all_rules()
    categories = get_all_categories()
    return render_template('rules.html', rules=all_rules, categories=categories)


# ==============================================================
# BUDGET PAGE
# ==============================================================

@app.route('/budget', methods=['GET', 'POST'])
def budget():
    """Budget page — set spending limits with smart suggestions based on history."""
    current_month = datetime.now().strftime('%Y-%m')
    selected_month = request.args.get('month', current_month)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'set':
            category = request.form.get('category')
            amount = float(request.form.get('amount', 0))
            set_budget(category, amount)
            flash(f'Budget set for {category}: ${amount:.2f}/month', 'success')

        elif action == 'delete':
            category = request.form.get('category')
            delete_budget(category)
            flash(f'Budget removed for {category}', 'success')

        elif action == 'prefill':
            # Pre-fill budgets based on average spending
            avg_spending = get_avg_spending_by_category()
            count = 0
            for cat, data in avg_spending.items():
                if cat != 'Uncategorized' and data['avg'] > 5:
                    # Round up to nearest $10 for a comfortable buffer
                    import math
                    rounded = math.ceil(data['avg'] / 10) * 10
                    set_budget(cat, rounded)
                    count += 1
            flash(f'Created {count} budgets based on your spending averages!', 'success')

        return redirect(url_for('budget', month=selected_month))

    # Gather all the data
    budgets = get_budgets()
    spending = get_spending_by_category_for_month(selected_month)
    categories = get_all_categories()
    avg_spending = get_avg_spending_by_category()
    history = get_monthly_spending_history(6)

    # Build budget cards with progress
    budget_data = []
    budgeted_categories = set()

    for b in budgets:
        cat = b['category']
        budgeted = b['amount']
        spent = spending.get(cat, 0)
        pct = min((spent / budgeted * 100), 100) if budgeted > 0 else 0
        over = spent > budgeted
        warning = not over and pct >= 80
        avg = avg_spending.get(cat, {}).get('avg', 0)
        budgeted_categories.add(cat)

        budget_data.append({
            'category': cat,
            'budgeted': budgeted,
            'spent': round(spent, 2),
            'remaining': round(budgeted - spent, 2),
            'percent': round(pct, 1),
            'over': over,
            'warning': warning,
            'avg': round(avg, 2),
            'history': history.get(cat, {})
        })

    # Add categories with spending this month but no budget
    for cat, spent in spending.items():
        if cat not in budgeted_categories:
            avg = avg_spending.get(cat, {}).get('avg', 0)
            budget_data.append({
                'category': cat,
                'budgeted': 0,
                'spent': round(spent, 2),
                'remaining': 0,
                'percent': 0,
                'over': False,
                'warning': False,
                'avg': round(avg, 2),
                'no_budget': True,
                'history': history.get(cat, {})
            })

    # Sort: over first, then warnings, then by percent desc
    budget_data.sort(key=lambda x: (-x.get('over', False), -x.get('warning', False), -x.get('percent', 0)))

    # Calculate totals
    total_budgeted = sum(b['budgeted'] for b in budget_data)
    total_spent = sum(b['spent'] for b in budget_data)
    has_budgets = any(b['budgeted'] > 0 for b in budget_data)

    # Suggestions: categories with spending but no budget
    suggestions = []
    for cat, data in avg_spending.items():
        if cat not in budgeted_categories and cat != 'Uncategorized' and data['avg'] > 5:
            import math
            suggestions.append({
                'category': cat,
                'avg': data['avg'],
                'suggested': math.ceil(data['avg'] / 10) * 10,
                'months': data['months']
            })
    suggestions.sort(key=lambda x: -x['avg'])

    return render_template('budget.html',
                           budget_data=budget_data,
                           categories=categories,
                           selected_month=selected_month,
                           current_month=current_month,
                           total_budgeted=total_budgeted,
                           total_spent=total_spent,
                           has_budgets=has_budgets,
                           suggestions=suggestions,
                           avg_spending=avg_spending)


# ==============================================================
# API ENDPOINTS (for AJAX calls from the dashboard)
# ==============================================================

@app.route('/api/transactions')
def api_transactions():
    transactions = get_all_transactions()
    return jsonify([dict(t) for t in transactions])


@app.route('/api/review', methods=['POST'])
def api_review():
    """Toggle a transaction's review status (AJAX endpoint)."""
    data = request.get_json()
    tid = data.get('id')
    reviewed = data.get('reviewed', True)
    update_transaction_review(tid, reviewed)
    return jsonify({'ok': True})


@app.route('/api/update-category', methods=['POST'])
def api_update_category():
    """Update a transaction's category (AJAX endpoint)."""
    data = request.get_json()
    tid = data.get('id')
    category = data.get('category')
    update_transaction_category(tid, category)
    return jsonify({'ok': True})


@app.route('/api/spending-by-category')
def api_spending_by_category():
    transactions = get_all_transactions()
    categories = {}
    for t in transactions:
        if t['amount'] < 0:
            cat = t['category'] or 'Uncategorized'
            categories[cat] = categories.get(cat, 0) + abs(t['amount'])
    sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
    return jsonify({
        'labels': [c[0] for c in sorted_cats],
        'values': [round(c[1], 2) for c in sorted_cats]
    })


@app.route('/api/transactions', methods=['POST'])
def api_create_transaction():
    """Manually add a single transaction (blueprint P0: Transaction CRUD)."""
    data = request.get_json()
    required = ['account_id', 'date', 'description', 'amount']
    if not all(data.get(k) is not None for k in required):
        return jsonify({'ok': False, 'error': 'Missing required fields'}), 400
    try:
        new_id = create_transaction(
            account_id=int(data['account_id']),
            date=data['date'],
            description=data['description'],
            amount=float(data['amount']),
            category=data.get('category', 'Uncategorized'),
            notes=data.get('notes', '')
        )
        return jsonify({'ok': True, 'id': new_id})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/transactions/<int:tid>', methods=['DELETE'])
def api_delete_transaction(tid):
    """Delete a transaction by ID."""
    try:
        delete_transaction(tid)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/transactions/<int:tid>', methods=['PUT'])
def api_update_transaction(tid):
    """Full update of a transaction."""
    data = request.get_json()
    required = ['date', 'description', 'amount']
    if not all(data.get(k) is not None for k in required):
        return jsonify({'ok': False, 'error': 'Missing required fields'}), 400
    try:
        update_transaction(
            tid,
            date=data['date'],
            description=data['description'],
            amount=float(data['amount']),
            category=data.get('category', 'Uncategorized'),
            notes=data.get('notes', '')
        )
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/monthly-summary')
def api_monthly_summary():
    transactions = get_all_transactions()
    months = {}
    for t in transactions:
        month_key = t['date'][:7]
        if month_key not in months:
            months[month_key] = {'income': 0, 'spent': 0}
        if t['amount'] > 0:
            months[month_key]['income'] += t['amount']
        else:
            months[month_key]['spent'] += abs(t['amount'])

    sorted_months = sorted(months.items())
    cumulative = 0
    result = []
    for month, data in sorted_months:
        cumulative += data['income'] - data['spent']
        result.append({
            'month': month,
            'income': round(data['income'], 2),
            'spent': round(data['spent'], 2),
            'balance': round(cumulative, 2)
        })
    return jsonify(result)


# ---- START THE APP ----
if __name__ == '__main__':
    initialize_database()
    print("\n🚀 Finance Tracker is running!")
    print("   Open http://localhost:5000 in your browser\n")
    app.run(debug=True, port=5000)
