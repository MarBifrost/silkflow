from flask import Blueprint, request, render_template, redirect, url_for, session
import MySQLdb.cursors

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        from app import mysql

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Check if account exists in MySQL
        cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s', (email, password))
        account = cursor.fetchone()

        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['email'] = account['email']
            return redirect(url_for('index'))
        else:
            msg = 'არასწორი იუზერი, ან პაროლი'

    return render_template('login.html', msg=msg)


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

