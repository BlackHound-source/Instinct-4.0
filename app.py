from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json
import os
from datetime import datetime
from collections import defaultdict
import glob

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# Simple user database (in production, use a real database)
USERS = {
    # Customers
    'customer1': {'password': 'pass123', 'role': 'customer', 'customer_id': 1, 'name': 'Customer_0'},
    'customer2': {'password': 'pass123', 'role': 'customer', 'customer_id': 50, 'name': 'Customer_49'},
    'customer3': {'password': 'pass123', 'role': 'customer', 'customer_id': 100, 'name': 'Customer_99'},

    # Engineers
    'ankit': {'password': 'eng123', 'role': 'engineer', 'engineer_name': 'Eng. Ankit', 'specialty': 'transformer'},
    'riya': {'password': 'eng123', 'role': 'engineer', 'engineer_name': 'Eng. Riya', 'specialty': 'line'},
    'suman': {'password': 'eng123', 'role': 'engineer', 'engineer_name': 'Eng. Suman', 'specialty': 'meter'},
    'arjun': {'password': 'eng123', 'role': 'engineer', 'engineer_name': 'Eng. Arjun', 'specialty': 'general'},
    'neha': {'password': 'eng123', 'role': 'engineer', 'engineer_name': 'Eng. Neha', 'specialty': 'line'},

    # Admin
    'admin': {'password': 'admin123', 'role': 'admin', 'name': 'System Administrator'}
}

# In-memory storage for issues, notifications, and task status
# In production, use a proper database
ISSUES = []
NOTIFICATIONS = []
TASK_STATUS = {}  # {customer_id: {'status': 'pending/in_progress/completed', 'engineer': 'name', 'notes': '...'}}


def load_issues():
    """Load issues from file."""
    try:
        if os.path.exists('issues.json'):
            with open('issues.json', 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return []


def save_issues():
    """Save issues to file."""
    try:
        with open('issues.json', 'w', encoding='utf-8') as f:
            json.dump(ISSUES, f, indent=2)
    except:
        pass


def load_notifications():
    """Load notifications from file."""
    try:
        if os.path.exists('notifications.json'):
            with open('notifications.json', 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return []


def save_notifications():
    """Save notifications to file."""
    try:
        with open('notifications.json', 'w', encoding='utf-8') as f:
            json.dump(NOTIFICATIONS, f, indent=2)
    except:
        pass


def load_task_status():
    """Load task status from file."""
    try:
        if os.path.exists('task_status.json'):
            with open('task_status.json', 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {}


def save_task_status():
    """Save task status to file."""
    try:
        with open('task_status.json', 'w', encoding='utf-8') as f:
            json.dump(TASK_STATUS, f, indent=2)
    except:
        pass


# Load data on startup
ISSUES = load_issues()
NOTIFICATIONS = load_notifications()
TASK_STATUS = load_task_status()


def get_latest_cycle_data():
    """Get the most recent cycle JSON file."""
    json_files = glob.glob('cycle_*.json')
    if not json_files:
        return None

    latest_file = max(json_files, key=os.path.getctime)

    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def get_all_cycle_data():
    """Get all cycle JSON files sorted by cycle number."""
    json_files = glob.glob('cycle_*.json')
    if not json_files:
        return []

    cycles = []
    for file in json_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                cycles.append(data)
        except:
            continue

    # Sort by cycle number
    cycles.sort(key=lambda x: x.get('cycle_number', 0))
    return cycles


def get_customer_history(customer_id):
    """Get fault history for a specific customer."""
    cycles = get_all_cycle_data()
    history = []

    for cycle in cycles:
        for fault in cycle.get('faults', []):
            if fault.get('customer_id') == customer_id:
                history.append({
                    'cycle': cycle.get('cycle_number'),
                    'timestamp': cycle.get('timestamp'),
                    'old_output': fault.get('old_output'),
                    'new_output': fault.get('new_output'),
                    'change_percentage': fault.get('change_percentage'),
                    'assigned_engineer': fault.get('assigned_engineer'),
                    'status': 'Resolved' if cycle.get('cycle_number', 0) < len(cycles) - 2 else 'Pending'
                })

    return history


def get_engineer_tasks(engineer_name):
    """Get current tasks for a specific engineer."""
    latest_data = get_latest_cycle_data()
    if not latest_data:
        return []

    tasks = []
    for fault in latest_data.get('faults', []):
        if fault.get('assigned_engineer') == engineer_name:
            tasks.append(fault)

    return tasks


@app.route('/')
def index():
    """Landing page with login."""
    if 'username' in session:
        role = session.get('role')
        if role == 'customer':
            return redirect(url_for('customer_dashboard'))
        elif role == 'engineer':
            return redirect(url_for('engineer_dashboard'))
        elif role == 'admin':
            return redirect(url_for('admin_dashboard'))

    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    """Handle login."""
    username = request.form.get('username')
    password = request.form.get('password')

    user = USERS.get(username)

    if user and user['password'] == password:
        session['username'] = username
        session['role'] = user['role']
        session['user_data'] = user

        if user['role'] == 'customer':
            return redirect(url_for('customer_dashboard'))
        elif user['role'] == 'engineer':
            return redirect(url_for('engineer_dashboard'))
        elif user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))

    return render_template('login.html', error='Invalid credentials')


@app.route('/logout')
def logout():
    """Handle logout."""
    session.clear()
    return redirect(url_for('index'))


@app.route('/customer')
def customer_dashboard():
    """Customer dashboard - view their meter status and history."""
    if 'username' not in session or session.get('role') != 'customer':
        return redirect(url_for('index'))

    user_data = session.get('user_data')
    customer_id = user_data.get('customer_id')

    # Get latest cycle data
    latest_data = get_latest_cycle_data()

    # Get customer's current status
    current_status = None
    if latest_data:
        for fault in latest_data.get('faults', []):
            if fault.get('customer_id') == customer_id:
                current_status = fault
                break

    # Get customer history
    history = get_customer_history(customer_id)

    # Get customer's issues
    customer_issues = [issue for issue in ISSUES if issue['customer_id'] == customer_id]

    # Get task status
    task_status = TASK_STATUS.get(str(customer_id))

    return render_template('customer_dashboard.html',
                           customer_id=customer_id,
                           customer_name=user_data.get('name'),
                           current_status=current_status,
                           history=history,
                           latest_cycle=latest_data,
                           issues=customer_issues,
                           task_status=task_status)


@app.route('/engineer')
def engineer_dashboard():
    """Engineer dashboard - view assigned tasks."""
    if 'username' not in session or session.get('role') != 'engineer':
        return redirect(url_for('index'))

    user_data = session.get('user_data')
    engineer_name = user_data.get('engineer_name')

    # Get current tasks from monitoring system
    tasks = get_engineer_tasks(engineer_name)

    # Get latest cycle info
    latest_data = get_latest_cycle_data()

    # Get assigned issues
    assigned_issues = [issue for issue in ISSUES if
                       issue.get('assigned_engineer') == engineer_name and issue['status'] != 'resolved']

    # Get notifications
    engineer_notifications = [notif for notif in NOTIFICATIONS if notif['engineer_name'] == engineer_name]
    unread_count = sum(1 for n in engineer_notifications if not n.get('read', False))

    # Calculate statistics
    total_tasks = len(tasks) + len(assigned_issues)
    high_priority = sum(1 for t in tasks if abs(t.get('change_percentage', 0)) > 150)
    high_priority += sum(1 for i in assigned_issues if i.get('priority') == 'high')

    # Get AI analysis for current tasks
    ai_insights = None
    if latest_data and latest_data.get('ai_analysis'):
        ai_insights = latest_data.get('ai_analysis')

    return render_template('engineer_dashboard.html',
                           engineer_name=engineer_name,
                           specialty=user_data.get('specialty'),
                           tasks=tasks,
                           assigned_issues=assigned_issues,
                           notifications=engineer_notifications[-10:],  # Last 10 notifications
                           unread_count=unread_count,
                           total_tasks=total_tasks,
                           high_priority=high_priority,
                           latest_cycle=latest_data,
                           ai_insights=ai_insights)


@app.route('/admin')
def admin_dashboard():
    """Admin dashboard - view all meters and system overview."""
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))

    # Get all cycle data
    cycles = get_all_cycle_data()

    # Get latest data
    latest_data = get_latest_cycle_data()

    # Calculate statistics
    stats = {
        'total_cycles': len(cycles),
        'total_customers': 1000,  # From your monitoring system
        'active_faults': latest_data.get('total_faults', 0) if latest_data else 0,
        'total_engineers': 5,
        'open_issues': sum(1 for i in ISSUES if i['status'] != 'resolved'),
        'total_issues': len(ISSUES)
    }

    # Get feeder and engineer summaries
    feeder_summary = latest_data.get('summary', {}).get('feeders', {}) if latest_data else {}
    engineer_summary = latest_data.get('summary', {}).get('engineers', {}) if latest_data else {}

    # Get AI analysis
    ai_analysis = latest_data.get('ai_analysis') if latest_data else None

    # Get all engineers for dropdown
    engineers = [
        'Eng. Ankit',
        'Eng. Riya',
        'Eng. Suman',
        'Eng. Arjun',
        'Eng. Neha'
    ]

    return render_template('admin_dashboard.html',
                           stats=stats,
                           latest_cycle=latest_data,
                           cycles=cycles[-10:],  # Last 10 cycles
                           feeder_summary=feeder_summary,
                           engineer_summary=engineer_summary,
                           ai_analysis=ai_analysis,
                           issues=ISSUES,
                           engineers=engineers)


@app.route('/api/latest-data')
def api_latest_data():
    """API endpoint to get latest cycle data."""
    data = get_latest_cycle_data()
    return jsonify(data if data else {})


@app.route('/api/customer/<int:customer_id>')
def api_customer_data(customer_id):
    """API endpoint to get specific customer data."""
    history = get_customer_history(customer_id)
    return jsonify(history)


@app.route('/api/engineer/<engineer_name>')
def api_engineer_tasks(engineer_name):
    """API endpoint to get engineer tasks."""
    tasks = get_engineer_tasks(engineer_name)
    return jsonify(tasks)


@app.route('/raise-issue', methods=['POST'])
def raise_issue():
    """Customer raises an issue."""
    if 'username' not in session or session.get('role') != 'customer':
        return jsonify({'error': 'Unauthorized'}), 401

    user_data = session.get('user_data')
    customer_id = user_data.get('customer_id')

    issue_data = {
        'id': len(ISSUES) + 1,
        'customer_id': customer_id,
        'customer_name': user_data.get('name'),
        'issue_type': request.form.get('issue_type'),
        'description': request.form.get('description'),
        'priority': request.form.get('priority', 'medium'),
        'status': 'open',
        'timestamp': datetime.now().isoformat(),
        'assigned_engineer': None
    }

    ISSUES.append(issue_data)
    save_issues()

    return redirect(url_for('customer_dashboard'))


@app.route('/assign-engineer', methods=['POST'])
def assign_engineer():
    """Admin assigns engineer to an issue."""
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401

    issue_id = int(request.form.get('issue_id'))
    engineer_name = request.form.get('engineer_name')

    # Find and update issue
    for issue in ISSUES:
        if issue['id'] == issue_id:
            issue['assigned_engineer'] = engineer_name
            issue['status'] = 'assigned'

            # Create notification for engineer
            notification = {
                'id': len(NOTIFICATIONS) + 1,
                'engineer_name': engineer_name,
                'issue_id': issue_id,
                'customer_id': issue['customer_id'],
                'message': f"New task assigned: {issue['issue_type']} for Customer #{issue['customer_id']}",
                'timestamp': datetime.now().isoformat(),
                'read': False
            }
            NOTIFICATIONS.append(notification)
            save_notifications()
            break

    save_issues()
    return redirect(url_for('admin_dashboard'))


@app.route('/update-task-status', methods=['POST'])
def update_task_status():
    """Engineer updates task status."""
    if 'username' not in session or session.get('role') != 'engineer':
        return jsonify({'error': 'Unauthorized'}), 401

    user_data = session.get('user_data')
    engineer_name = user_data.get('engineer_name')

    customer_id = request.form.get('customer_id')
    status = request.form.get('status')
    notes = request.form.get('notes', '')

    # Update task status
    TASK_STATUS[customer_id] = {
        'status': status,
        'engineer': engineer_name,
        'notes': notes,
        'timestamp': datetime.now().isoformat()
    }
    save_task_status()

    # Mark notifications as read
    for notification in NOTIFICATIONS:
        if notification['engineer_name'] == engineer_name and str(notification['customer_id']) == customer_id:
            notification['read'] = True
    save_notifications()

    return redirect(url_for('engineer_dashboard'))


@app.route('/mark-issue-resolved', methods=['POST'])
def mark_issue_resolved():
    """Engineer marks issue as resolved."""
    if 'username' not in session or session.get('role') != 'engineer':
        return jsonify({'error': 'Unauthorized'}), 401

    issue_id = int(request.form.get('issue_id'))
    notes = request.form.get('notes', '')

    # Find and update issue
    for issue in ISSUES:
        if issue['id'] == issue_id:
            issue['status'] = 'resolved'
            issue['resolution_notes'] = notes
            issue['resolved_at'] = datetime.now().isoformat()
            break

    save_issues()
    return redirect(url_for('engineer_dashboard'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)