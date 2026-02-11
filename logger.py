import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
from functools import wraps
from flask import session, request


#create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.mkdir('logs')


#=========================================================================#
#    shift logger - tracks daily shifts, vacations and its replacements   #
#=========================================================================#
shift_logger = logging.getLogger('shift_logger')
shift_logger.setLevel(logging.INFO)

shift_handler = RotatingFileHandler(
    'logs/shift_log.log',
    maxBytes=1024 * 1024 * 10, #10mb
    backupCount=10,
)

shift_formatter = logging.Formatter(
    '%(asctime)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

shift_handler.setFormatter(shift_formatter)
shift_logger.addHandler(shift_handler)


# ======================================================#
# AUTH LOGGER - Tracks user authentication and actions  #
# ======================================================#

auth_logger = logging.getLogger('auth_logger')
auth_logger.setLevel(logging.INFO)

auth_handler = RotatingFileHandler(
    'logs/auth.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=10
)
auth_formatter = logging.Formatter(
    '%(asctime)s | USER: %(user)s | IP: %(ip)s | ACTION: %(action)s | DETAILS: %(details)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
auth_handler.setFormatter(auth_formatter)
auth_logger.addHandler(auth_handler)



# ========================#
# LOGGING FUNCTIONS       #
# ========================#
def log_shift_assignment (shift_date, employee_name, is_replacement=False, original_employee=None, reason=None):
    """
        Log shift assignments including replacements

        Args:
            shift_date: Date of the shift
            employee_name: Name of the employee on shift
            is_replacement: Whether this is a replacement shift
            original_employee: Name of the original employee (if replacement)
            reason: Reason for replacement (e.g., vacation)
    """
    if is_replacement and original_employee:
        message = f"SHIFT | Date: {shift_date} | Employee: {employee_name} | REPLACING: {original_employee} | Reason: {reason or 'Not specified'}"
    else:
        message = f"SHIFT | Date: {shift_date} | Employee: {employee_name} | Type: Regular shift"

    shift_logger.info(message)

def log_vacation(employee_name, start_date, end_date, action='ADDED'):
    """
        Log vacation requests

        Args:
            employee_name: Name of the employee
            start_date: Vacation start date
            end_date: Vacation end date
            action: Action type (ADDED, DELETED)
    """
    message = f"VACATION {action} | Employee: {employee_name} | Period: {start_date} to {end_date}"
    shift_logger.info(message)


def log_daily_shifts(shifts_data):
    """
    Log all shifts for a specific day

    Args:
        shifts_data: List of shift dictionaries with date, employee, replacement info
    """
    if not shifts_data:
        return

    shift_logger.info("=" * 80)
    shift_logger.info(f"DAILY SHIFT REPORT")
    shift_logger.info("=" * 80)

    for shift in shifts_data:
        log_shift_assignment(
            shift_date=shift.get('shift_date'),
            employee_name=shift.get('employee_name'),
            is_replacement=shift.get('is_replacement', False),
            original_employee=shift.get('original_employee'),
            reason=shift.get('reason')
        )

    shift_logger.info("=" * 80)


def log_auth_event(action, details='', user_email=None):
    """
    Log authentication and user action events

    Args:
        action: Type of action (LOGIN, LOGOUT, ADD_CLASS, DELETE_CLASS, etc.)
        details: Additional details about the action
        user_email: User email (defaults to session email)
    """
    user = user_email or session.get('email', 'Unknown')
    ip = request.remote_addr if request else 'Unknown'

    auth_logger.info(
        '',
        extra={
            'user': user,
            'ip': ip,
            'action': action,
            'details': details
        }
    )


# ================================
# DECORATOR FOR AUTO-LOGGING
# ================================

def log_action(action_name):
    """
    Decorator to automatically log user actions

    Usage:
        @log_action('ADD_CLASS')
        def add_class():
            ...
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = session.get('email', 'Unknown')
            log_auth_event(action_name, f"Function: {f.__name__}")
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# ================================
# UTILITY FUNCTIONS
# ================================

def get_shift_logs(date=None, employee=None, limit=100):
    """
    Read and filter shift logs

    Args:
        date: Filter by specific date (YYYY-MM-DD)
        employee: Filter by employee name
        limit: Maximum number of lines to return

    Returns:
        List of log entries
    """
    try:
        with open('logs/shifts.log', 'r', encoding='utf-8') as f:
            lines = f.readlines()

        filtered = []
        for line in lines[-limit:]:
            if date and date not in line:
                continue
            if employee and employee not in line:
                continue
            filtered.append(line.strip())

        return filtered
    except FileNotFoundError:
        return []


def get_auth_logs(user=None, action=None, limit=100):
    """
    Read and filter authentication logs

    Args:
        user: Filter by user email
        action: Filter by action type
        limit: Maximum number of lines to return

    Returns:
        List of log entries
    """
    try:
        with open('logs/auth.log', 'r', encoding='utf-8') as f:
            lines = f.readlines()

        filtered = []
        for line in lines[-limit:]:
            if user and user not in line:
                continue
            if action and action not in line:
                continue
            filtered.append(line.strip())

        return filtered
    except FileNotFoundError:
        return []