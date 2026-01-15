from flask import Flask, render_template, session, redirect, url_for, request, jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
from auth import auth_bp
from datetime import datetime, timedelta
import pytz

app = Flask(__name__)
app.secret_key = 'mariam123'

app.config['MYSQL_HOST'] = '10.240.0.39'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'qwe123'
app.config['MYSQL_DB'] = 'silkflow_users'

mysql = MySQL(app)

app.register_blueprint(auth_bp)


@app.route('/')
def index():
    if 'loggedin' in session:
        return redirect(url_for('main'))
    return redirect(url_for('auth.login'))

@app.route('/class')
def my_class():
    if 'loggedin' not in session:
        return redirect(url_for('auth.login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    course_name = request.args.get('course_name')
    mentor_name = request.args.get('mentor_name')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    days_of_week = request.args.get('days_of_week')
    duration = request.args.get('duration')


    query = 'SELECT * FROM courses limit 2'
    cursor.execute(query)
    course = cursor.fetchall()
    cursor.close()

    return render_template('class.html', course=course, course_name = course_name, mentor_name=mentor_name,start_date=start_date,end_date=end_date,days_of_week=days_of_week,duration=duration)



@app.route('/main')
def main():
    if 'loggedin' not in session:
        return redirect(url_for('auth.login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    tbilisi_tz = pytz.timezone('Asia/Tbilisi')
    today = datetime.now(tbilisi_tz).date()

    search_keyword = request.args.get('searchKeyword')
    chosen_date = request.args.get('filter_date')

    start_date = chosen_date if chosen_date else today

    if search_keyword:
        limit_date = today + timedelta(days=30)
        query = """
            SELECT s.shift_date, DAYNAME(s.shift_date) as day_name, e.name as employee_name 
            FROM shifts s 
            LEFT JOIN employees e ON s.employee_id = e.id 
            WHERE e.name LIKE %s AND s.shift_date BETWEEN %s AND %s
            ORDER BY s.shift_date
        """
        cursor.execute(query, (f"%{search_keyword}%", today, limit_date))
    else:
        start_date = chosen_date if chosen_date else today
        query = """
            SELECT s.shift_date, DAYNAME(s.shift_date) as day_name, e.name as employee_name 
            FROM shifts s 
            LEFT JOIN employees e ON s.employee_id = e.id 
            WHERE s.shift_date >= %s 
            ORDER BY s.shift_date 
            LIMIT 7
        """
        cursor.execute(query, (start_date,))

    shifts = cursor.fetchall()
    cursor.close()

    for shift in shifts:
        if shift['shift_date']:
            shift['shift_date'] = shift['shift_date'].strftime('%Y-%m-%d')

    return render_template('main.html', shifts=shifts, email=session.get('email'))





if __name__ == '__main__':
    app.run(debug=True)