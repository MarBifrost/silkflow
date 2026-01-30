# auth.py – cleaned up version

from flask import Blueprint, request, render_template, redirect, url_for, session
from database import get_db

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
                return redirect(url_for('index'))   # or 'main.index' etc.
            else:
                msg = 'არასწორი ელ.ფოსტა ან პაროლი'

        except Exception as e:   # better to catch DB errors
            print(f"Database error during login: {e}")
            msg = 'მოხდა შეცდომა. სცადეთ მოგვიანებით'

    return render_template('login.html', msg=msg)


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))