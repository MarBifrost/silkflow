from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from logger import get_shift_logs, get_auth_logs
from auth import is_admin
from datetime import datetime, timedelta

logs_bp = Blueprint('logs', __name__, template_folder='templates')


@logs_bp.route('/logs')
def view_logs():
    """Main logs viewing page - requires admin access"""
    if 'loggedin' not in session:
        return redirect(url_for('auth.login'))

    if not is_admin():
        flash('მხოლოდ ადმინისტრატორს აქვს წვდომა ლოგებზე', 'danger')
        return redirect(url_for('main'))

    log_type = request.args.get('type', 'auth')  # 'auth' or 'shift'
    date_filter = request.args.get('date', '')
    user_filter = request.args.get('user', '')
    action_filter = request.args.get('action', '')
    employee_filter = request.args.get('employee', '')
    limit = int(request.args.get('limit', 100))

    logs = []

    if log_type == 'auth':
        logs = get_auth_logs(
            user=user_filter if user_filter else None,
            action=action_filter if action_filter else None,
            limit=limit
        )
    else:  # shift logs
        logs = get_shift_logs(
            date=date_filter if date_filter else None,
            employee=employee_filter if employee_filter else None,
            limit=limit
        )

    return render_template('logs.html',
                           logs=logs,
                           log_type=log_type,
                           date_filter=date_filter,
                           user_filter=user_filter,
                           action_filter=action_filter,
                           employee_filter=employee_filter,
                           limit=limit)


@logs_bp.route('/logs/download')
def download_logs():
    """Download raw log files - requires admin access"""
    if 'loggedin' not in session:
        return redirect(url_for('auth.login'))

    if not is_admin():
        flash('მხოლოდ ადმინისტრატორს აქვს წვდომა ლოგებზე', 'danger')
        return redirect(url_for('main'))

    log_type = request.args.get('type', 'auth')

    from flask import send_file

    if log_type == 'auth':
        return send_file('logs/auth.log',
                         mimetype='text/plain',
                         as_attachment=True,
                         download_name=f'auth_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    else:
        return send_file('logs/shifts.log',
                         mimetype='text/plain',
                         as_attachment=True,
                         download_name=f'shifts_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')