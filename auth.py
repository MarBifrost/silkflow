from flask import Blueprint, request, render_template, redirect, url_for, session
from database import get_db
from logger import log_auth_event


auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not email or not password:
            msg = 'შეიყვანეთ ელ.ფოსტა და პაროლი'
            return render_template('login.html', msg=msg)

        try:
            db = get_db()
            cursor = db.cursor()

            cursor.execute(
                'SELECT * FROM employees  WHERE email = %s AND password = %s',
                (email, password)
            )
            account = cursor.fetchone()


            if account:
                session['loggedin'] = True
                session['id']       = account['id']
                session['email']    = account['email']
                session['role']     = account['role']

                # Log successful login
                log_auth_event('LOGIN_SUCCESS',
                               f"User: {account.get('name')} (Role: {account.get('role')})",
                               user_email=email)
                return redirect(url_for('index'))   # or 'main.index' etc.
            else:
                log_auth_event('LOGIN_FAILED',
                               f"Failed login attempt for email: {email}",
                               user_email=email)
                msg = 'არასწორი ელ.ფოსტა ან პაროლი'

        except Exception as e:   # better to catch DB errors
            print(f"Database error during login: {e}")
            msg = 'მოხდა შეცდომა. სცადეთ მოგვიანებით'

    return render_template('login.html', msg=msg)


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


def is_admin():
    """ამოწმებს, არის თუ არა მომხმარებელი ადმინი"""
    return session.get('role') == 'admin'