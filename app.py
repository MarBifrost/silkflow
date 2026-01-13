from flask import Flask, render_template, session, redirect, url_for, request, jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
from auth import auth_bp # Import the blueprint

app = Flask(__name__)
app.secret_key = 'mariam123'

# MySQL Configurations
app.config['MYSQL_HOST'] = '10.240.0.39'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'qwe123'
app.config['MYSQL_DB'] = 'silkflow_users'

mysql = MySQL(app)

# Register the Blueprint
app.register_blueprint(auth_bp)

@app.route('/')
def index():
    if 'loggedin' in session:
        return render_template('main.html', email=session['email'])
    return redirect(url_for('auth.login'))

@app.route('/main')
def main_page():
    if request.method == "GET":
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        query = 'SELECT shifts.shift_date, employees.name FROM shifts join employees on shifts.employee_id = employee.id;'
        cursor.execute(query)
        shifts = cursor.fetchall()
        cursor.close()

        for shift in shifts:
            if shift['shift_date']:
                shift['shift_date'] = shift['shift_date'].strftime('%Y-%m-%d')

        return jsonify(shifts)
if __name__ == '__main__':
    app.run(debug=True)