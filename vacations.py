from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from contextlib import contextmanager
from database import init_db, get_db

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

vacations_bp = Blueprint('vacations', __name__, template_folder='templates')

ka_names = {
    "Mariam":"მარიამ",
    "Zura":"ზურა",
    "Giorgi":"გიორგი",
    "Beqa":"ბექა",
    "Saba":"საბა"
}


@vacations_bp.route('/vacations')
def vacations():
    if 'loggedin' not in session:
        return redirect(url_for('auth.login'))

    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT id, name FROM employees ORDER BY name")
            employees_list = cursor.fetchall()

            # All vacations with readable names, newest first
            query = """
                SELECT
                    v.id,
                    e1.name AS employee_name,
                    v.start_date,
                    v.end_date
                FROM vacations v
                JOIN employees e1 ON v.employee_id = e1.id
                ORDER BY v.start_date DESC
            """
            cursor.execute(query)
            vacations_with_names = cursor.fetchall()

            for vacation in vacations_with_names:
                if vacation['employee_name']:
                    georgian_name = vacation['employee_name']
                    vacation['employee_name'] = ka_names.get(georgian_name, georgian_name)


            return render_template(
                'vacations.html',
                employees=employees_list,
                vacations=vacations_with_names
            )

    except Exception as e:
        flash(f"Error loading vacations: {str(e)}", "danger")
        return redirect(url_for('main'))


@vacations_bp.route('/add_vacation', methods=['POST'])
def add_vacation():
    if 'loggedin' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    emp_id = request.form['employee_id']
    s_date = request.form['start_date']
    e_date = request.form['end_date']

    if not all([emp_id, s_date, e_date]):
        flash("ყველა ველი სავალდებულოა", "danger")
        return redirect(url_for('vacations.vacations'))

    try:
        with get_db_cursor() as cursor:
            if s_date > e_date:
                flash("არასწორი დრო", "danger")
                return redirect(url_for('vacations.vacations'))

            #გადაფარვის შემოწმება
            cursor.execute("""
                        SELECT 1 FROM vacations 
                        WHERE employee_id = %s 
                        LIMIT 1
                    """, (emp_id,))

            if cursor.fetchone():
                flash("შვებულება უკვე გაფორმებულია, ახალს ვერ დაამატებთ", "danger")
                return redirect(url_for('vacations.vacations'))


            #insert vacation
            cursor.execute("""
                insert into vacations
                (employee_id, start_date, end_date)
                values (%s, %s, %s)
            """, (emp_id, s_date, e_date))

            #clear employee from shifts during vacation
            cursor.execute("""
                update shifts set replacement_reason = 9 
                where employee_id = %s
                and shift_date between %s and %s
            """, (emp_id, s_date, e_date))

        db.commit()
        # flash ("შვებულება წარმატებით დაემატა", "success")


    except Exception as e:
        db.rollback()
        flash(f"Error loading vacations: {str(e)}", "danger")
        print("Vacation error:", str(e))

    return redirect(url_for('vacations.vacations'))


@vacations_bp.route('/delete_vacation/<int:id>', methods=['POST', 'GET'])
def delete_vacation(id):
    if 'loggedin' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    try:
        with get_db_cursor() as cursor:
            # 1. Fetch the vacation details before deleting
            cursor.execute("SELECT * FROM vacations WHERE id = %s", (id,))
            vacation = cursor.fetchone()

            if not vacation:
                flash("Vacation record not found", "danger")
                return redirect(url_for('vacations.vacations'))

            # 2. Restore the shifts
            cursor.execute("""
                            UPDATE shifts 
                            SET replacement_reason = NULL
                            WHERE employee_id = %s 
                              AND shift_date BETWEEN %s AND %s
            """, (
                vacation['employee_id'],
                vacation['start_date'],
                vacation['end_date']
            ))

            # 3. Delete the vacation record
            cursor.execute("DELETE FROM vacations WHERE id = %s", (id,))

            db.commit()

    except Exception as e:
        db.rollback()
        # Log the error to your console for easier debugging
        print(f"Database Error: {e}")
        flash("An error occurred while deleting the vacation.", "danger")

    return redirect(url_for('vacations.vacations'))


# @vacations_bp.route('/edit_vacation/<int:id>', methods=['GET', 'POST'])
# def edit_vacation(id):
#     if 'loggedin' not in session:
#         return redirect(url_for('auth.login'))
#
#     db = get_db()
#     current_user_emp_id = session['employee_id']
#
#     try:
#         with get_db_cursor() as cursor:
#             #არსებული შვებულება
#             cursor.execute("SELECT * FROM vacations WHERE id = %s", (id,))
#             vacation = cursor.fetchone()
#
#             if not vacation:
#                 flash("შვებულება არ მოიძებნა", "danger")
#                 return redirect(url_for('vacations.vacations'))
#
#             #უფლების შემოწმება - მხოლოდ თავისი რომ მოძებნოს
#             if vacation['employee_id'] != current_user_emp_id:
#                 flash("მხოლოდ თქვენი შვებულების რედაქტირება შეგიძლიათ")
#                 return redirect(url_for('vacations.vacations'))
#
#             s_date = request.form.get('start_date')
#             e_date = request.form.get('end_date')
#
#             if s_date > e_date:
#                 flash("არასწორი დრო", "danger")
#                 return redirect(url_for('vacations.vacations'))
#
#             #შევამოწმოთ ხომ არ არის შვებულება ამ დროებში
#             cursor.execute("""
#                             select 1 from vacations where employee_id = %s
#                             and id != %s
#                             and start_date <= %s
#                             and end_date >= %s
#                             limit 1
#
#             """, (current_user_emp_id, id, s_date, e_date))
#
#             if cursor.fetchone():
#                 flash("შვებულება უკვე გაფორმებულია ამ პერიოდში, ახალს ვერ შექმნით", "danger")
#                 return redirect(url_for('vacations.vacations'))
#
#             #ძველი პერიოდის გათავისუფლება
#             old_start = vacation['start_date']
#             old_end = vacation['end_date']
#
#             cursor.execute("""
#                             update shifts set replacement_reason = NULL
#                             where employee_id = %s
#                             and shift_date between %s and %s
#                             """, (current_user_emp_id, old_start, old_end))
#
#             #ახალზე ბეისზე შეცვლა 9-ით
#             cursor.execute("""
#                             UPDATE shifts
#                             SET replacement_reason = 9
#                             WHERE employee_id = %s
#                             AND shift_date BETWEEN %s AND %s
#                         """, (current_user_emp_id, s_date, e_date))
#
#             # 6. vacations ცხრილის განახლება
#             cursor.execute("""
#                     UPDATE vacations
#                     SET start_date = %s, end_date = %s
#                     WHERE id = %s
#                 """, (s_date, e_date, id))
#
#             db.commit()
#             flash("შვებულება წარმატებით განახლდა", "success")
#
#     except Exception as e:
#         db.rollback()
#         flash(f"შეცდომა რედაქტირებისას: {str(e)}", "danger")
#         print("Edit vacation error:", str(e))
#
#     return redirect(url_for('vacations.vacations'))