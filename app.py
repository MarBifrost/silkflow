from flask import Flask, render_template, session, redirect, url_for, request, flash
from database import init_db, get_db
import MySQLdb.cursors
from auth import auth_bp
from vacations import vacations_bp
from datetime import datetime, timedelta
import pytz


app = Flask(__name__)
app.secret_key = 'mariam123'

app.config['MYSQL_HOST'] = '10.240.0.39'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'qwe123'
app.config['MYSQL_DB'] = 'silkflow_users'

init_db(app)


app.register_blueprint(auth_bp)
app.register_blueprint(vacations_bp)

#employee cponfig

ka_names = {
    "Mariam":"მარიამ",
    "Zura":"ზურა",
    "Giorgi":"გიორგი",
    "Beqa":"ბექა",
    "Saba":"საბა"
}

ka_weekdays = {
    'Monday':    'ორშაბათი',
    'Tuesday':   'სამშაბათი',
    'Wednesday': 'ოთხშაბათი',
    'Thursday':  'ხუთშაბათი',
    'Friday':    'პარასკევი',
    'Saturday':  'შაბათი',
    'Sunday':    'კვირა'
}

@app.route('/')
def index():
    if 'loggedin' in session:
        return redirect(url_for('main'))
    return redirect(url_for('auth.login'))

@app.route('/class')
def my_class():
    db = get_db()
    cursor = db.cursor()
    if 'loggedin' not in session:
        return redirect(url_for('auth.login'))

    try:
        query = 'SELECT * FROM courses LIMIT 2'
        cursor.execute(query)
        course_list = cursor.fetchall()

        return render_template('class.html', course=course_list)

    except Exception as e:
        flash(f"Error loading classes: {str(e)}", "danger")
        return redirect(url_for('main'))


@app.route('/main')
def main():
    db = get_db()
    cursor = db.cursor()
    if 'loggedin' not in session:
        return redirect(url_for('auth.login'))

    try:
        tbilisi_tz = pytz.timezone('Asia/Tbilisi')
        today = datetime.now(tbilisi_tz).date()

        search_keyword = request.args.get('searchkeyword', '').strip()
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
            query = """
                    SELECT s.shift_date, DAYNAME(s.shift_date) as day_name, e.name as employee_name
                    FROM shifts s
                    LEFT JOIN employees e ON s.employee_id = e.id
                    WHERE s.shift_date >= %s
                    ORDER BY s.shift_date
                    LIMIT 14
                """
            cursor.execute(query, (start_date,))



        shifts = cursor.fetchall()

        for shift in shifts:
            if shift['shift_date']:
                shift['shift_date'] = shift['shift_date'].strftime('%Y-%m-%d')
            english_day = shift['day_name']
            shift['day_name'] = ka_weekdays.get(english_day, english_day)

            georgian_name = shift['employee_name']
            shift['employee_name'] = ka_names.get( georgian_name,  georgian_name)

        return render_template('main.html', shifts=shifts, email=session.get('email'))

    except Exception as e:
        flash(f"Error loading schedule: {str(e)}", "danger")
        return render_template('main.html', shifts=[], email=session.get('email'))



if __name__ == '__main__':
    app.run(debug=True)







