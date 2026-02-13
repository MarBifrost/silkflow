from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from contextlib import contextmanager
from database import init_db, get_db
from logger import log_vacation, log_auth_event, log_shift_assignment


vacations_bp = Blueprint('vacations', __name__, template_folder='templates')

ka_names = {
    "Mariam":"მარიამ",
    "Zura":"ზურა",
    "Giorgi":"გიორგი",
    "Beqa":"ბექა",
    "Saba":"საბა"
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


def get_georgian_name(name: str) -> str:
    return ka_names.get(name, name)


def get_employees() -> List[Tuple[int, str]]:
    with get_db_cursor() as cur:
        cur.execute('SELECT * FROM employees')


def assign_replacements(cursor):
    today = datetime.now().date()
    lookback_date = today - timedelta(days=30)

    #ვიღებთყველას მორიგეობას
    cursor.execute("""
        select * from shifts where (employee_id is not null)
    """)



@vacations_bp.route('/vacations')
def vacations():
    if 'loggedin' not in session:
        return redirect(url_for('auth.login'))
    # Log page access
    log_auth_event('VIEW_VACATIONS', 'Accessed vacations page')


    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT id, name FROM employees where role != 'admin' ORDER BY name")
            employees_list = cursor.fetchall()

            # All vacations with readable names and email, newest first
            query = """
                SELECT
                    v.id,
                    e1.name AS employee_name,
                    e1.email,
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

            # Get employee name for logging
            cursor.execute("SELECT name FROM employees WHERE id = %s", (emp_id,))
            employee = cursor.fetchone()
            employee_name = employee['name'] if employee else f"ID:{emp_id}"


            #გადაფარვის შემოწმება
            cursor.execute("""
                        SELECT 1 FROM vacations 
                        WHERE employee_id = %s 
                        LIMIT 1
                    """, (emp_id,))

            if cursor.fetchone():
                log_auth_event('ADD_VACATION_FAILED', f'Duplicate vacation for employee: {employee_name}')
                flash("შვებულება უკვე გაფორმებულია, ახალს ვერ დაამატებთ", "danger")
                return redirect(url_for('vacations.vacations'))


            #insert vacation
            cursor.execute("""
                insert into vacations
                (employee_id, start_date, end_date)
                values (%s, %s, %s)
            """, (emp_id, s_date, e_date))

            affected_shifts = cursor.rowcount

            #clear employee from shifts during vacation
            cursor.execute("""
                update shifts set replacement_reason = 9 
                where employee_id = %s
                and shift_date between %s and %s
            """, (emp_id, s_date, e_date))

        db.commit()

        # Log successful vacation addition
        log_vacation(employee_name, s_date, e_date, action='ADDED')
        log_auth_event('ADD_VACATION',
                       f'Employee: {employee_name}, Period: {s_date} to {e_date}, Affected shifts: {affected_shifts}')
        # flash ("შვებულება წარმატებით დაემატა", "success")


    except Exception as e:
        db.rollback()
        log_auth_event('ADD_VACATION_ERROR', f'Database error: {str(e)}')
        flash(f"Error loading vacations: {str(e)}", "danger")
        print("Vacation error:", str(e))

    return redirect(url_for('vacations.vacations'))


@vacations_bp.route('/delete_vacation/<int:id>', methods=['POST', 'GET'])
def delete_vacation(id):
    if 'loggedin' not in session:
        return redirect(url_for('auth.login'))

    db = get_db()
    try:
        with db.cursor() as cursor:
            # 1. ვიღებთ შვებულებას id-ით
            cursor.execute("SELECT * FROM vacations WHERE id = %s", (id,))
            vacation = cursor.fetchone()

            if not vacation:
                log_auth_event('DELETE_VACATION_FAILED', f'Vacation not found: ID {id}')
                flash("შვებულება ვერ მოიძებნა", "danger")
                return redirect(url_for('vacations.vacations'))

            # 2. ვამოწმებთ უფლებას
            current_user_id = session['id']           # ← აქ არის შენი ID
            is_admin = session.get('role') == 'admin'
            is_owner = vacation['employee_id'] == current_user_id

            if not (is_admin or is_owner):
                log_auth_event('DELETE_VACATION_DENIED',
                              f'Unauthorized attempt to delete vacation ID {id} for {vacation["employee_name"]}')
                flash("თქვენ არ გაქვთ უფლება წაშალოთ ეს შვებულება", "danger")
                return redirect(url_for('vacations.vacations'))

            # 3. აღვადგენთ მორიგეობებს (replacement_reason = NULL)
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
            restored_shifts = cursor.rowcount

            # 4. ვშლით შვებულებას
            cursor.execute("DELETE FROM vacations WHERE id = %s", (id,))

            db.commit()
            # Log successful deletion
            log_vacation(vacation['employee_name'],
                         vacation['start_date'],
                         vacation['end_date'],
                         action='DELETED')
            log_auth_event('DELETE_VACATION',
                           f'Employee: {vacation["employee_name"]}, Period: {vacation["start_date"]} to {vacation["end_date"]}, Restored shifts: {restored_shifts}')

            flash("შვებულება წარმატებით წაიშალა", "success")

    except Exception as e:
        db.rollback()
        log_auth_event('DELETE_VACATION_ERROR', f'Error deleting vacation ID {id}: {str(e)}')
        print(f"Error deleting vacation ID {id}: {e}")
        flash("შეცდომა შვებულების წაშლისას", "danger")

    return redirect(url_for('vacations.vacations'))
