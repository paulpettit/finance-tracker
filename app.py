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
import calendar
from collections import defaultdict
from io import StringIO
from datetime import datetime, date, timedelta
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, jsonify, session, Response)
from database.models import (
    initialize_database, add_account, get_or_create_account, add_transactions,
    get_all_transactions, get_all_accounts, get_all_categories,
    get_recent_uploads,
    update_transaction_review, update_transaction_category, get_review_stats,
    create_transaction, delete_transaction, update_transaction,
    add_rule, get_all_rules, delete_rule, toggle_rule, apply_rules_retroactively,
    get_rule_match_counts, preview_rule_matches, update_rule_priority,
    set_budget, get_budgets, delete_budget, get_spending_by_category_for_month,
    get_avg_spending_by_category, get_monthly_spending_history
)
from parsers import get_parser, PARSERS

# ---- APP SETUP ----
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-fallback-key-change-in-production')
initialize_database()

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def _budget_summary(month=None):
    """Build a compact budget summary for dashboard widgets and APIs."""
    month = month or datetime.now().strftime('%Y-%m')
    budgets = get_budgets(month)
    spending = get_spending_by_category_for_month(month)
    avg_spending = get_avg_spending_by_category()

    budgeted_categories = {b['category'] for b in budgets}
    total_budgeted = sum(b['amount'] for b in budgets)
    total_spent = sum(spending.values())
    over = []
    warning = []
    ok = []

    for b in budgets:
        cat = b['category']
        amount = b['amount']
        spent = spending.get(cat, 0)
        pct = (spent / amount * 100) if amount > 0 else 0
        item = {
            'category': cat,
            'budgeted': round(amount, 2),
            'spent': round(spent, 2),
            'remaining': round(amount - spent, 2),
            'percent': round(min(pct, 100), 1),
            'average': round(avg_spending.get(cat, {}).get('avg', 0), 2)
        }
        if spent > amount:
            over.append(item)
        elif pct >= 80:
            warning.append(item)
        else:
            ok.append(item)

    unbudgeted = [
        {'category': cat, 'spent': round(amount, 2)}
        for cat, amount in spending.items()
        if cat not in budgeted_categories
    ]

    return {
        'month': month,
        'total_budgeted': round(total_budgeted, 2),
        'total_spent': round(total_spent, 2),
        'remaining': round(total_budgeted - total_spent, 2),
        'percent': round(min((total_spent / total_budgeted * 100), 100), 1) if total_budgeted else 0,
        'has_budgets': total_budgeted > 0,
        'over': over,
        'warning': warning,
        'ok_count': len(ok),
        'over_count': len(over),
        'warning_count': len(warning),
        'unbudgeted_count': len(unbudgeted),
        'unbudgeted': sorted(unbudgeted, key=lambda x: -x['spent'])[:5]
    }


def _shift_sample_transactions_to_current_month(transactions):
    """Keep sample data feeling current by moving dates into the active month."""
    today = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    shifted = []
    for tx in transactions:
        day = int(tx['date'][-2:])
        clone = dict(tx)
        clone['date'] = date(today.year, today.month, min(day, last_day)).strftime('%Y-%m-%d')
        shifted.append(clone)
    return shifted


# ==============================================================
# DASHBOARD
# ==============================================================

@app.route('/')
def index():
    """Landing / get-started page."""
    return render_template('landing.html')


def _format_tx_date(d, today):
    """Friendly date label for the activity table."""
    try:
        dt = datetime.strptime(d, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return d
    if dt == today:
        return 'Today'
    if dt == today - timedelta(days=1):
        return 'Yesterday'
    if dt.year == today.year:
        return dt.strftime('%b %-d')
    return dt.strftime('%b %-d, %Y')


def _build_dashboard_chart(transactions, today):
    """
    Build SVG path data for the 30-day spending chart.
    Returns dict with path, area, last_x/y, quietest point, and axis labels.
    """
    W, H, P = 720, 220, 18
    days = 30
    start = today - timedelta(days=days - 1)
    daily = [0.0] * days
    for t in transactions:
        if t['amount'] >= 0:
            continue
        try:
            dt = datetime.strptime(t['date'], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            continue
        if dt < start or dt > today:
            continue
        daily[(dt - start).days] += -t['amount']

    if not any(daily):
        return {
            'spending_path': '', 'spending_area': '',
            'last_x': 0, 'last_y': 0,
            'quietest_x': None, 'quietest_y': 0,
            'quietest_pct': 0, 'quietest_label': None,
            'chart_x_labels': [
                start.strftime('%b %-d'),
                (start + timedelta(days=10)).strftime('%b %-d'),
                (start + timedelta(days=20)).strftime('%b %-d'),
                'Today',
            ],
        }

    max_v = max(daily) or 1.0
    step = (W - P * 2) / (days - 1)
    pts = []
    for i, v in enumerate(daily):
        x = P + i * step
        y = H - P - (v / max_v) * (H - P * 2)
        pts.append((x, y))
    path = ' '.join(
        ('M' if i == 0 else 'L') + f'{x:.1f},{y:.1f}'
        for i, (x, y) in enumerate(pts)
    )
    area = path + f' L{pts[-1][0]:.1f},{H - P} L{P},{H - P} Z'

    # Pick the quietest non-zero day for the annotation. If everything is
    # zero we already returned above.
    nonzero = [(i, v) for i, v in enumerate(daily) if v > 0]
    quiet_i = min(nonzero, key=lambda iv: iv[1])[0] if nonzero else 0
    quiet_x, quiet_y = pts[quiet_i]
    quiet_date = start + timedelta(days=quiet_i)

    return {
        'spending_path': path,
        'spending_area': area,
        'last_x': pts[-1][0],
        'last_y': pts[-1][1],
        'quietest_x': quiet_x,
        'quietest_y': quiet_y,
        'quietest_pct': (quiet_x / W) * 100,
        'quietest_label': quiet_date.strftime('%b %-d'),
        'chart_x_labels': [
            start.strftime('%b %-d'),
            (start + timedelta(days=10)).strftime('%b %-d'),
            (start + timedelta(days=20)).strftime('%b %-d'),
            'Today',
        ],
    }


def _build_account_balances(accounts, transactions):
    """Compute a balance per account by summing its transactions."""
    sums = defaultdict(float)
    for t in transactions:
        sums[t['account_id']] += t['amount']
    out = []
    for a in accounts:
        a_dict = dict(a)
        a_dict['balance'] = round(sums.get(a['id'], 0.0), 2)
        out.append(a_dict)
    return out


def _build_insight(transactions, today):
    """
    Pick an interesting "moment" for the dashboard insight card.
    Compare this month's spend by category to the prior 3-month average and
    surface the biggest jump. Returns None if there isn't a clear story.
    """
    month_start = today.replace(day=1)
    prior_start = (month_start - timedelta(days=1)).replace(day=1)
    # 3 prior months of dates: start = month_start - 90 days, roughly.
    three_prior_start = (month_start - timedelta(days=92)).replace(day=1)

    this_month = defaultdict(lambda: {'amount': 0.0, 'count': 0})
    prior = defaultdict(lambda: {'amount': 0.0, 'months': set()})
    for t in transactions:
        if t['amount'] >= 0:
            continue
        try:
            dt = datetime.strptime(t['date'], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            continue
        cat = t['category'] or 'Uncategorized'
        if cat == 'Uncategorized':
            continue
        if dt >= month_start and dt <= today:
            this_month[cat]['amount'] += -t['amount']
            this_month[cat]['count'] += 1
        elif three_prior_start <= dt < month_start:
            prior[cat]['amount'] += -t['amount']
            prior[cat]['months'].add(dt.strftime('%Y-%m'))

    best = None
    for cat, cur in this_month.items():
        if cur['amount'] < 50:  # not enough money to be interesting
            continue
        prior_data = prior.get(cat)
        prior_avg = (prior_data['amount'] / max(1, len(prior_data['months']))) if prior_data else 0
        delta = cur['amount'] - prior_avg
        if delta <= 0:
            continue
        # Prefer the biggest absolute jump over baseline.
        if best is None or delta > best['_delta']:
            best = {
                'category': cat,
                'amount': round(cur['amount'], 2),
                'tx_count': cur['count'],
                '_delta': delta,
                '_prior_avg': prior_avg,
            }

    if not best:
        return None

    if best['_prior_avg'] > 0:
        annual = best['amount'] * 12
        detail = f"more than your prior 3-month average of ${best['_prior_avg']:,.0f}. At this pace, ${annual:,.0f} a year."
    else:
        detail = f"a new line item this month, on {best['tx_count']} transaction{'s' if best['tx_count'] != 1 else ''}."

    return {
        'category': best['category'],
        'amount': best['amount'],
        'tx_count': best['tx_count'],
        'detail': detail,
    }


@app.route('/dashboard')
def dashboard():
    accounts = get_all_accounts()
    transactions = get_all_transactions()
    review_stats = get_review_stats()

    today = date.today()
    month_start = today.replace(day=1)
    has_data = bool(transactions)

    # Whole-month income / spent from positive vs negative transactions.
    month_income = 0.0
    month_spent = 0.0
    month_tx_count = 0
    for t in transactions:
        try:
            dt = datetime.strptime(t['date'], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            continue
        if dt < month_start or dt > today:
            continue
        month_tx_count += 1
        if t['amount'] > 0:
            month_income += t['amount']
        else:
            month_spent += -t['amount']
    month_net = round(month_income - month_spent, 2)

    accounts_with_balance = _build_account_balances(accounts, transactions)
    total_balance = sum(a['balance'] for a in accounts_with_balance)
    balance_whole = int(total_balance)
    balance_cents = f"{int(round((total_balance - balance_whole) * 100)):02d}"

    chart = _build_dashboard_chart(transactions, today)

    large_unreviewed = sum(
        1 for t in transactions
        if not t['reviewed'] and abs(t['amount']) > 100
    )

    # Top categories with budget context.
    budget_summary = _budget_summary()
    current_month_key = today.strftime('%Y-%m')
    spending = get_spending_by_category_for_month(current_month_key)
    budgets = {b['category']: b['amount'] for b in get_budgets(current_month_key)}
    top_cats_raw = sorted(
        ((cat, amt) for cat, amt in spending.items() if cat != 'Uncategorized'),
        key=lambda kv: -kv[1]
    )[:5]
    top_categories = []
    for cat, spent in top_cats_raw:
        budgeted = budgets.get(cat, 0)
        pct = round(min((spent / budgeted) * 100, 100), 1) if budgeted else 0
        top_categories.append({
            'category': cat,
            'spent': round(spent, 2),
            'budgeted': budgeted,
            'percent': pct,
            'over': budgeted and spent > budgeted,
        })

    # Recent activity (top 12) with friendly date labels.
    recent_transactions = []
    for t in transactions[:12]:
        d = dict(t)
        d['date_label'] = _format_tx_date(t['date'], today)
        recent_transactions.append(d)

    insight = _build_insight(transactions, today)

    return render_template(
        'index.html',
        has_data=has_data,
        accounts=accounts_with_balance,
        recent_transactions=recent_transactions,
        total_transactions=len(transactions),
        review_stats=review_stats,
        budget_summary=budget_summary,
        balance_whole=balance_whole,
        balance_cents=balance_cents,
        month_income=round(month_income, 2),
        month_spent=round(month_spent, 2),
        month_net=month_net,
        month_tx_count=month_tx_count,
        large_unreviewed=large_unreviewed,
        top_categories=top_categories,
        month_label=today.strftime('%B'),
        today_label=today.strftime('%A, %B %-d, %Y'),
        issue_label=f'№ {today.strftime("%B %Y")}',
        insight=insight,
        **chart,
    )


@app.route('/sample-data', methods=['POST'])
def sample_data():
    """Load the bundled fake CSV into the current month for first-run exploration."""
    sample_path = os.path.join(os.path.dirname(__file__), 'sample_data', 'chase_sample.csv')
    parser = get_parser('chase_checking')

    if not parser or not os.path.exists(sample_path):
        flash('Sample data is unavailable.', 'error')
        return redirect(url_for('dashboard'))

    with open(sample_path, 'r', encoding='utf-8-sig') as f:
        transactions = _shift_sample_transactions_to_current_month(parser.parse(f.read()))

    account_id = get_or_create_account('Sample Chase Checking', 'chase', 'checking')
    count, skipped = add_transactions(transactions, account_id, 'sample_data/chase_sample.csv')

    current_month = datetime.now().strftime('%Y-%m')
    default_budgets = {
        'Food & Drink': 350,
        'Shopping': 300,
        'Transportation': 180,
        'Housing': 1800,
        'Utilities': 250,
        'Subscriptions': 75
    }
    for category, amount in default_budgets.items():
        set_budget(category, amount, current_month)

    if count:
        flash(f'Loaded {count} sample transactions and starter budgets.', 'success')
    else:
        flash(f'Sample data is already loaded. {skipped} duplicates skipped.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/export.csv')
def export_csv():
    """Download all transactions as a CSV."""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['date', 'description', 'amount', 'category', 'account', 'institution', 'source_file', 'reviewed', 'notes'])
    accounts = {a['id']: a for a in get_all_accounts()}
    for t in get_all_transactions():
        account = accounts.get(t['account_id'])
        writer.writerow([
            t['date'],
            t['description'],
            t['amount'],
            t['category'],
            account['name'] if account else '',
            account['institution'] if account else '',
            t['source_file'] or '',
            'yes' if t['reviewed'] else 'no',
            t['notes'] or ''
        ])

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=finance-tracker-transactions.csv'}
    )


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
    return render_template('upload.html',
                           parsers=available_parsers,
                           step='upload',
                           recent_uploads=get_recent_uploads())


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
                                       recent_uploads=get_recent_uploads(),
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

    suggested_columns = _suggest_csv_columns(headers)

    return render_template('upload.html',
                           step='map_columns',
                           headers=headers,
                           suggested_columns=suggested_columns,
                           sample_rows=rows,
                           filename=file.filename,
                           account_name=account_name,
                           recent_uploads=get_recent_uploads(),
                           parsers=list(PARSERS.keys()))


def _suggest_csv_columns(headers):
    """Best-effort defaults for the generic CSV mapper."""
    def normalize(value):
        return ''.join(ch for ch in value.lower() if ch.isalnum())

    normalized = [(header, normalize(header)) for header in headers]

    def find(candidates, fallback_index=0, exclude=None):
        exclude = set(exclude or [])
        for header, key in normalized:
            if header in exclude:
                continue
            if any(candidate in key for candidate in candidates):
                return header
        for header in headers:
            if header not in exclude:
                return header
        return ''

    date_col = find(('date', 'posted', 'posting', 'transactiondate'), 0)
    desc_col = find(('description', 'merchant', 'payee', 'name', 'memo', 'details'), 1, {date_col})
    amount_col = find(('amount', 'debit', 'credit', 'value'), 2, {date_col, desc_col})
    category_col = find(('category', 'type'), 3, {date_col, desc_col, amount_col})
    if category_col in {date_col, desc_col, amount_col}:
        category_col = ''

    return {
        'date': date_col,
        'description': desc_col,
        'amount': amount_col,
        'category': category_col,
    }


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

    account_id = get_or_create_account(account_name, inst_name, acct_type)
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
            existing_id = request.form.get('rule_id', '').strip()
            if existing_id:
                delete_rule(int(existing_id))
            add_rule(
                name=request.form.get('name', 'New Rule'),
                condition_field=request.form.get('condition_field', 'description'),
                condition_op=request.form.get('condition_op', 'contains'),
                condition_value=request.form.get('condition_value', ''),
                action_category=request.form.get('action_category') or None,
                action_rename=request.form.get('action_rename') or None
            )
            flash('Rule updated!' if existing_id else 'Rule created!', 'success')

        elif action == 'delete':
            delete_rule(int(request.form.get('rule_id')))
            flash('Rule deleted', 'success')

        elif action == 'toggle':
            toggle_rule(int(request.form.get('rule_id')))
            flash('Rule toggled', 'success')

        elif action == 'priority':
            rule_id = int(request.form.get('rule_id'))
            direction = request.form.get('direction', 'up')
            update_rule_priority(rule_id, direction)
            flash('Rule priority updated', 'success')

        elif action == 'apply_all':
            updated = apply_rules_retroactively()
            flash(f'Rules applied! {updated} transactions updated.', 'success')

        return redirect(url_for('rules'))

    all_rules = get_all_rules()
    categories = get_all_categories()
    match_counts = get_rule_match_counts()
    matched_recent = sum(c['recent'] for c in match_counts.values())
    review_stats = get_review_stats()
    return render_template(
        'rules.html',
        rules=all_rules,
        categories=categories,
        match_counts=match_counts,
        matched_recent=matched_recent,
        review_unreviewed=review_stats['unreviewed'],
    )


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
            set_budget(category, amount, selected_month)
            flash(f'Budget set for {category} in {selected_month}: ${amount:.2f}/month', 'success')

        elif action == 'delete':
            category = request.form.get('category')
            delete_budget(category, selected_month)
            flash(f'Budget removed for {category} in {selected_month}', 'success')

        elif action == 'prefill':
            # Pre-fill budgets based on average spending
            avg_spending = get_avg_spending_by_category()
            count = 0
            for cat, data in avg_spending.items():
                if cat != 'Uncategorized' and data['avg'] > 5:
                    # Round up to nearest $10 for a comfortable buffer
                    import math
                    rounded = math.ceil(data['avg'] / 10) * 10
                    set_budget(cat, rounded, selected_month)
                    count += 1
            flash(f'Created {count} budgets for {selected_month} based on your spending averages!', 'success')

        return redirect(url_for('budget', month=selected_month))

    # Gather all the data
    budgets = get_budgets(selected_month)
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

    _y, _m = int(selected_month[:4]), int(selected_month[5:7])
    _last = calendar.monthrange(_y, _m)[1]
    days_remaining = max(0, (date(_y, _m, _last) - date.today()).days)
    if selected_month == current_month:
        elapsed_days = min(date.today().day, _last)
    elif selected_month < current_month:
        elapsed_days = _last
    else:
        elapsed_days = 0
    expected_spent = total_budgeted * (elapsed_days / _last) if total_budgeted > 0 else 0
    pacing_delta = round(expected_spent - total_spent, 2)

    # 6-month history strip
    month_total_history = get_monthly_spending_history(6)
    month_totals = defaultdict(float)
    for cat_months in month_total_history.values():
        for m, v in cat_months.items():
            month_totals[m] += v

    history_months = []
    cursor_y, cursor_m = _y, _m
    months_back = []
    for _ in range(6):
        months_back.append(f"{cursor_y:04d}-{cursor_m:02d}")
        cursor_m -= 1
        if cursor_m == 0:
            cursor_m = 12
            cursor_y -= 1
    months_back.reverse()
    for m_key in months_back:
        m_budgets = get_budgets(m_key)
        m_budget_total = sum(b['amount'] for b in m_budgets)
        m_spent = round(month_totals.get(m_key, 0), 2)
        history_months.append({
            'label': datetime.strptime(m_key, '%Y-%m').strftime('%b'),
            'spent': m_spent,
            'budget': m_budget_total,
            'over': m_budget_total > 0 and m_spent > m_budget_total,
            'current': m_key == selected_month,
        })
    history_max = max(
        max((m['spent'] for m in history_months), default=0),
        max((m['budget'] for m in history_months), default=0),
        1,
    )

    month_pretty = datetime.strptime(selected_month, '%Y-%m').strftime('%B %Y')

    return render_template(
        'budget.html',
        budget_data=budget_data,
        categories=categories,
        selected_month=selected_month,
        current_month=current_month,
        total_budgeted=total_budgeted,
        total_spent=total_spent,
        has_budgets=has_budgets,
        suggestions=suggestions,
        avg_spending=avg_spending,
        days_remaining=days_remaining,
        pacing_delta=pacing_delta,
        elapsed_days=elapsed_days,
        month_days=_last,
        month_pretty=month_pretty,
        history_months=history_months,
        history_max=history_max,
        issue_label=f'№ {month_pretty}',
    )


# ==============================================================
# API ENDPOINTS (for AJAX calls from the dashboard)
# ==============================================================

@app.route('/api/transactions')
def api_transactions():
    transactions = get_all_transactions()
    return jsonify([dict(t) for t in transactions])


@app.route('/api/accounts', methods=['POST'])
def api_create_account():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    account_type = data.get('account_type') or 'checking'
    institution = data.get('institution') or 'manual'

    if not name:
        return jsonify({'ok': False, 'error': 'Account name is required'}), 400

    try:
        account_id = add_account(name, institution, account_type)
        return jsonify({'ok': True, 'id': account_id})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


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
    required = ['account_id', 'date', 'description', 'amount']
    if not all(data.get(k) is not None for k in required):
        return jsonify({'ok': False, 'error': 'Missing required fields'}), 400
    try:
        update_transaction(
            tid,
            account_id=int(data['account_id']),
            date=data['date'],
            description=data['description'],
            amount=float(data['amount']),
            category=data.get('category', 'Uncategorized'),
            notes=data.get('notes', '')
        )
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/budget-summary')
def api_budget_summary():
    month = request.args.get('month') or datetime.now().strftime('%Y-%m')
    return jsonify(_budget_summary(month))


@app.route('/api/rules/preview', methods=['POST'])
def api_rule_preview():
    data = request.get_json() or {}
    value = (data.get('condition_value') or '').strip()
    if not value:
        return jsonify({'ok': True, 'count': 0, 'matches': []})

    matches = preview_rule_matches(
        data.get('condition_field', 'description'),
        data.get('condition_op', 'contains'),
        value,
        limit=5
    )
    return jsonify({
        'ok': True,
        'count': len(matches),
        'matches': [{
            'id': m['id'],
            'date': m['date'],
            'description': m['description'],
            'amount': m['amount'],
            'category': m['category']
        } for m in matches]
    })


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
    print("\nFinance Tracker is running!")
    print("   Open http://localhost:5000 in your browser\n")
    app.run(debug=True, port=5000)
