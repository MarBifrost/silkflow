from flask import Flask, render_template, session, redirect, url_for, request, flash
from database import init_db, get_db
from contextlib import contextmanager
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

# employee config
ka_names = {
    "Mariam": "მარიამ",
    "Zura": "ზურა",
    "Giorgi": "გიორგი",
    "Beqa": "ბექა",
    "Saba": "საბა"
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


@contextmanager
def get_db_cursor():
    db = get_db()
    cursor = db.cursor()
    try:
        yield cursor
        db.commit()
    except Exception as e:
        db.rollback()
        raise
    finally:
        cursor.close()


@app.route('/')
def index():
    if 'loggedin' in session:
        return redirect(url_for('main'))
    return redirect(url_for('auth.login'))


# --------------------------------#
#        კურსების ნაწილი          #
# --------------------------------#
@app.route('/class')
def my_class():
    if 'loggedin' not in session:
        return redirect(url_for('auth.login'))

    try:
        with get_db_cursor() as cursor:
            cursor.execute('SELECT * FROM courses')
            course_list = cursor.fetchall()
        return render_template('class.html', course=course_list)

    except Exception as e:
        flash(f"Error loading classes: {str(e)}", "danger")
        return redirect(url_for('main'))


@app.route('/add_class', methods=['POST'])
def add_class():
    if 'loggedin' not in session:
        return redirect(url_for('auth.login'))

    c_name = request.form.get('course_name')
    m_name = request.form.get('mentor_name')
    s_date = request.form.get('start_date')
    e_date = request.form.get('end_date')
    w_days = request.form.get('days_of_week')
    class_time = request.form.get('class_time')
    duration = request.form.get('duration')

    if not all([c_name, m_name, s_date, e_date, w_days, class_time, duration]):
        flash("ყველა ველი სავალდებულოა", "danger")
        return redirect(url_for('my_class'))

    try:
        with get_db_cursor() as cursor:
            if s_date > e_date or not w_days:
                flash("არასწორი დრო ან დღეები", "danger")
                return redirect(url_for('my_class'))

            cursor.execute("SELECT 1 FROM courses WHERE course_name = %s LIMIT 1", (c_name,))
            if cursor.fetchone():
                flash("კურსი ასეთი სახელით უკვე დამატებულია", "danger")
                return redirect(url_for('my_class'))

            cursor.execute("""
                INSERT INTO courses 
                (course_name, mentor_name, start_date, end_date, days_of_week, class_time, duration)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (c_name, m_name, s_date, e_date, w_days, class_time, duration))

        flash("კურსი წარმატებით დაემატა", "success")
    except Exception as e:
        flash(f"Error adding class: {str(e)}", "danger")
        print("Courses error:", str(e))

    return redirect(url_for('my_class'))


@app.route('/delete_class/<int:id>', methods=['POST'])
def delete_course(id):
    if 'loggedin' not in session:
        return redirect(url_for('auth.login'))

    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM courses WHERE id = %s", (id,))
            course = cursor.fetchone()

            if not course:
                flash("კურსი არ მოიძებნა", "danger")
                return redirect(url_for('my_class'))

            cursor.execute("DELETE FROM courses WHERE id = %s", (id,))

        flash(f"კურსი „{course['course_name']}“ წაიშალა", "success")
    except Exception as e:
        flash(f"Error deleting class: {str(e)}", "danger")
        print("Courses error:", str(e))

    return redirect(url_for('my_class'))


# --------------------------------#
#   კურსების ნაწილის დასასრული    #
# --------------------------------#


def find_replacement(shift_date, excluded_emp_id, cursor):
    query = """
            SELECT e.name
            FROM employees e
            LEFT JOIN shifts s 
                ON e.id = s.employee_id 
                AND s.shift_date BETWEEN DATE_SUB(%s, INTERVAL 30 DAY) AND DATE_SUB(%s, INTERVAL 1 DAY)
                AND s.replacement_reason IS NULL
            WHERE e.id != %s
              AND NOT EXISTS (
                  SELECT 1 
                  FROM shifts vs 
                  WHERE vs.employee_id = e.id 
                    AND vs.shift_date = %s 
                    AND vs.replacement_reason = 9
              )
            AND NOT EXISTS (
                  SELECT 1 
                  FROM shifts rs 
                  WHERE rs.employee_id = e.id 
                    AND rs.shift_date BETWEEN DATE_SUB(%s, INTERVAL 30 DAY) AND DATE_SUB(%s, INTERVAL 1 DAY)
                    AND rs.replacement_reason IS NOT NULL
              )
            GROUP BY e.id, e.name
            ORDER BY COUNT(s.id) ASC, e.name ASC
            LIMIT 1
        """
    cursor.execute(query, (shift_date, shift_date, excluded_emp_id, shift_date, shift_date, shift_date))
    result = cursor.fetchone()
    return result['name'] if result else None

@app.route('/main')
def main():
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
            # თუ ქართული სახელია → ვპოულობთ ინგლისურს ბაზისთვის
            for en_name, ka_name in ka_names.items():
                if search_keyword == ka_name:
                    db_search_term = en_name
                    break

        with get_db_cursor() as cursor:
            if search_keyword:
                limit_date = today + timedelta(days=30)
                query = """
                    SELECT s.shift_date, DAYNAME(s.shift_date) as day_name, 
                           e.name as employee_name, s.employee_id, s.replacement_reason
                    FROM shifts s
                    LEFT JOIN employees e ON s.employee_id = e.id
                    WHERE e.name LIKE %s 
                      AND s.shift_date BETWEEN %s AND %s
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
                orig_name_en = shift['employee_name']
                shift_date_str = shift['shift_date'].strftime('%Y-%m-%d') if shift['shift_date'] else ''

                if shift.get('replacement_reason') == 9:
                    replacer_name_en = find_replacement(
                        shift['shift_date'],
                        shift['employee_id'],
                        cursor
                    )

                    if replacer_name_en:
                        replacer_ka = ka_names.get(replacer_name_en, replacer_name_en)
                        absent_ka = ka_names.get(orig_name_en, orig_name_en)
                        shift['employee_name'] = f"{replacer_ka} (ანაცვლებს {absent_ka}ს)"
                    else:
                        absent_ka = ka_names.get(orig_name_en, orig_name_en)
                        shift['employee_name'] = f"{absent_ka} (შემცვლელი არ მოიძებნა)"
                else:
                    shift['employee_name'] = ka_names.get(orig_name_en, orig_name_en)

                shift['shift_date'] = shift_date_str
                english_day = shift['day_name']
                shift['day_name'] = ka_weekdays.get(english_day, english_day)

        return render_template('main.html', shifts=shifts, email=session.get('email'))

    except Exception as e:
        flash(f"Error loading schedule: {str(e)}", "danger")
        print("Main error:", str(e))
        return render_template('main.html', shifts=[], email=session.get('email'))


if __name__ == '__main__':
    app.run(debug=True)