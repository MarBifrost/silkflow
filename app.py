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

employees = ["მარიამ", "ზურა", "გიორგი", "საბა", "ბექა"]
anchor_date = datetime(2026, 1, 1).date()


def count_workdays(target_date):
    if target_date < anchor_date:
        return 0
    count = 0
    current =  anchor_date
    while current < target_date:
        if current.weekday() != 6:
            count += 1
        current += timedelta(days=1)
    return count

ka_weekdays = {
    'Monday':    'ორშაბათი',
    'Tuesday':   'სამშაბათი',
    'Wednesday': 'ოთხშაბათი',
    'Thursday':  'ხუთშაბათი',
    'Friday':    'პარასკევი',
    'Saturday':  'შაბათი',
    'Sunday':    'კვირა'
}


#start_date-დან დაწყებით ცვლების გამოთვლა, დააბრუნებს "დასვენების დღეს"
def generate_shifts(start_date, days=90):
    """
    გენერირებს ცვლებს start_date-დან days რაოდენობის წინ.
    თანამშრომლები ფიქსირდება ANCHOR_DATE-დან.
    """
    shifts = []
    current = start_date

    for _ in range(days):
        weekday = current.weekday()
        date_str = current.strftime('%Y-%m-%d')
        day_name = ka_weekdays [current.strftime('%A')]

        if weekday != 6:
            # გამოთვლა ფიქსირებული ინდექსი
            workdays_passed = count_workdays(current)
            employee_index = workdays_passed % len(employees)
            employee = employees[employee_index]
        else:
            employee = "დასვენების დღე"

        shifts.append({
            'shift_date': date_str,
            'day_name': day_name,
            'employee_name': employee
        })

        current += timedelta(days=1)

    return shifts

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
    tbilisi_tz = pytz.timezone('Asia/Tbilisi')
    today = datetime.now(tbilisi_tz).date()
    if 'loggedin' not in session:
        return redirect(url_for('auth.login'))

    try:
        chosen_date_str = request.args.get('filter_date')
        if chosen_date_str:
            try:
                start_date = datetime.strptime(chosen_date_str, '%Y-%m-%d').date()
            except ValueError:
                start_date = today
                flash("არასწორი თარიღის ფორმატი — გამოიყენება დღევანდელი თარიღი", "warning")
        else:
            start_date = today

        search_keyword = request.args.get('search_keyword', '').strip().lower()

        # გენერირება საკმარისი დღეების (მაგ. 90, რომ თვე გაეტიოს)
        all_shifts = generate_shifts(start_date, days=90)

        if search_keyword:
            # თუ სახელი მითითებულია — ფილტრი იმ თანამშრომლის ცვლებზე + ერთ თვეში (დღევანდელიდან)
            end_date = today + timedelta(days=14)  # ერთი თვე წინ
            filtered_shifts = [
                s for s in all_shifts
                if search_keyword in s['employee_name'].lower()
            ]
        else:
            # თუ სახელი არ არის — ყველა ცვლა, მაგრამ შეზღუდული 35 დღით დღევანდელიდან
            filtered_shifts = [
                s for s in all_shifts
                if datetime.strptime(s['shift_date'], '%Y-%m-%d').date() >= today
            ][:35]

        return render_template(
            'main.html',
            shifts=filtered_shifts,
            email=session.get('email'),
            today=today.strftime('%Y-%m-%d'),
            search_keyword=search_keyword,
            filter_date=chosen_date_str or today.strftime('%Y-%m-%d')
        )

    except Exception as e:
        flash(f"შეცდომა გრაფიკის ჩატვირთვისას: {str(e)}", "danger")
        return render_template(
            'main.html',
            shifts=[],
            email=session.get('email'),
            today=today.strftime('%Y-%m-%d')
        )



if __name__ == '__main__':
    app.run(debug=True)







