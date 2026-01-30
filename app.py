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

#employee config

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

def find_replacement(shift_date, excluded_emp_id, cursor):
    query = """
            SELECT 
                e.id, 
                e.name,
                COUNT(s_count.id) AS shift_count_last_30
            FROM employees e
            LEFT JOIN shifts s_count 
                ON e.id = s_count.employee_id 
                AND s_count.shift_date BETWEEN DATE_SUB(%s, INTERVAL 30 DAY) AND DATE_SUB(%s, INTERVAL 1 DAY)
                AND (s_count.replacement_reason IS NULL OR s_count.replacement_reason != 9)  -- მხოლოდ რეალური მორიგეობები
            LEFT JOIN shifts s_today 
                ON e.id = s_today.employee_id 
                AND s_today.shift_date = %s
            WHERE e.id != %s
              AND s_today.id IS NULL          -- საერთოდ არ აქვს ჩანაწერი დღეს → არა მორიგე და არა შვებულებაში
            GROUP BY e.id, e.name
            ORDER BY shift_count_last_30 ASC
            LIMIT 1
    """
    try:
        cursor.execute(query, (shift_date, shift_date, shift_date, excluded_emp_id))
        result = cursor.fetchone()
        return result['name'] if result else None
    except Exception as e:
        print(f"Error finding replacement: {e}")
        return None

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

        db_search_term = search_keyword
        if search_keyword:
            # ვეძებთ ქართულ სახელს ჩვენს ლექსიკონში და ვიღებთ შესაბამის ინგლისურ გასაღებს
            for en_name, ka_name in ka_names.items():
                if search_keyword == ka_name:
                    db_search_term = en_name
                    break

        if search_keyword:
            limit_date = today + timedelta(days=30)
            query = """
                            SELECT s.shift_date, DAYNAME(s.shift_date) as day_name, 
                                   e.name as employee_name, s.employee_id, s.replacement_reason
                            FROM shifts s
                            LEFT JOIN employees e ON s.employee_id = e.id
                            WHERE e.name LIKE %s AND s.shift_date BETWEEN %s AND %s
                            ORDER BY s.shift_date
                        """
            cursor.execute(query, (f"%{db_search_term}%", today, limit_date))
        else:
            query = """
                            SELECT s.shift_date, DAYNAME(s.shift_date) as day_name, 
                                   e.name as employee_name, s.employee_id, s.replacement_reason
                            FROM shifts s
                            LEFT JOIN employees e ON s.employee_id = e.id
                            WHERE s.shift_date >= %s
                            ORDER BY s.shift_date
                            LIMIT 14
                        """
            cursor.execute(query, (start_date,))

        shifts = cursor.fetchall()
        for shift in shifts:
            # 1. ამოვიღოთ ორიგინალი სახელი (ინგლისურად რაცაა ბაზაში)
            orig_name_en = shift['employee_name']

            # 2. შევამოწმოთ, არის თუ არა შვებულებაში (replacement_reason == 9)
            if shift.get('replacement_reason') == 9:
                # ვიპოვოთ შემცვლელი (ყველაზე ნაკლები მორიგეობით)
                cursor.execute("""
                            SELECT e.name FROM employees e
                            LEFT JOIN shifts s ON e.id = s.employee_id 
                                 AND s.shift_date BETWEEN DATE_SUB(%s, INTERVAL 30 DAY) AND DATE_SUB(%s, INTERVAL 1 DAY)
                            WHERE e.id != %s
                            GROUP BY e.id
                            ORDER BY COUNT(s.id) ASC LIMIT 1
                        """, (shift['shift_date'], shift['shift_date'], shift['employee_id']))

                replacer = cursor.fetchone()

                if replacer:
                    name_b = ka_names.get(replacer['name'], replacer['name'])
                    name_a = ka_names.get(orig_name_en, orig_name_en)
                    shift['employee_name'] = f"{name_b} (ანაცვლებს {name_a}ს)"
                else:
                    shift['employee_name'] = ka_names.get(orig_name_en, orig_name_en)
            else:
                # თუ შვებულებაში არაა, ჩვეულებრივად გადავთარგმნოთ
                shift['employee_name'] = ka_names.get(orig_name_en, orig_name_en)
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







