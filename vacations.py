from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import MySQLdb.cursors
from database import init_db, mysql

vacations_bp = Blueprint('vacations', __name__, template_folder='templates')


@vacations_bp.route('/vacations')
def vacations():
    if 'loggedin' not in session:
        return redirect(url_for('auth.login'))

    try:
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            # Employees for the dropdown
            cursor.execute("SELECT id, name FROM employees ORDER BY name")
            employees_list = cursor.fetchall()

            # All vacations with readable names, newest first
            query = """
                SELECT
                    v.id,
                    e1.name AS employee_name,
                    e2.name AS substitute_name,
                    v.start_date,
                    v.end_date
                FROM vacations v
                JOIN employees e1 ON v.employee_id = e1.id
                JOIN employees e2 ON v.substitute_id = e2.id
                ORDER BY v.start_date DESC
            """
            cursor.execute(query)
            vacations_with_names = cursor.fetchall()

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
    from app import mysql
    if 'loggedin' not in session:
        return redirect(url_for('auth.login'))

    # Safely get and convert form values
    try:
        emp_id = int(request.form.get('employee_id'))
        sub_id = int(request.form.get('substitute_id'))
        s_date = request.form.get('start_date')
        e_date = request.form.get('end_date')
    except (ValueError, TypeError):
        flash("Invalid input: employee or substitute ID is not a number", "danger")
        return redirect(url_for('vacations.vacations'))

    if not all([emp_id, sub_id, s_date, e_date]):
        flash("All fields are required", "danger")
        return redirect(url_for('vacations.vacations'))

    if emp_id == sub_id:
        flash("Employee and substitute cannot be the same person", "danger")
        return redirect(url_for('vacations.vacations'))

    if s_date > e_date:
        flash("Start date cannot be after end date", "danger")
        return redirect(url_for('vacations.vacations'))

    try:
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:

            # ────────────────────────────────────────────────
            # 1. Employee already has overlapping vacation
            cursor.execute("""
                SELECT 1 FROM vacations
                WHERE employee_id = %s
                  AND start_date <= %s
                  AND end_date   >= %s
                LIMIT 1
            """, (emp_id, e_date, s_date))

            if cursor.fetchone():
                flash("This employee already has an overlapping vacation", "danger")
                return redirect(url_for('vacations.vacations'))

            # ────────────────────────────────────────────────
            # 2. Substitute is already on vacation (as employee)
            cursor.execute("""
                SELECT 1 FROM vacations
                WHERE employee_id = %s
                  AND start_date <= %s
                  AND end_date   >= %s
                LIMIT 1
            """, (sub_id, e_date, s_date))

            if cursor.fetchone():
                flash("The chosen substitute is already on vacation during this period", "danger")
                return redirect(url_for('vacations.vacations'))

            # ────────────────────────────────────────────────
            # 3. Substitute is already covering someone else
            cursor.execute("""
                SELECT 1 FROM vacations
                WHERE substitute_id = %s
                  AND start_date <= %s
                  AND end_date   >= %s
                LIMIT 1
            """, (sub_id, e_date, s_date))

            if cursor.fetchone():
                flash("The chosen substitute is already replacing someone else in this period", "danger")
                return redirect(url_for('vacations.vacations'))

            # ────────────────────────────────────────────────
            # All checks passed → create vacation & update shifts
            cursor.execute("""
                INSERT INTO vacations
                (employee_id, substitute_id, start_date, end_date)
                VALUES (%s, %s, %s, %s)
            """, (emp_id, sub_id, s_date, e_date))

            cursor.execute("""
                UPDATE shifts
                SET employee_id = %s
                WHERE employee_id = %s
                  AND shift_date BETWEEN %s AND %s
            """, (sub_id, emp_id, s_date, e_date))

        mysql.connection.commit()
        flash("Vacation added successfully. Shifts updated with substitute.", "success")

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Database error while adding vacation: {str(e)}", "danger")

    return redirect(url_for('vacations.vacations'))


@vacations_bp.route('/delete_vacation/<int:id>')
def delete_vacation(id):
    from app import mysql
    if 'loggedin' not in session:
        return redirect(url_for('auth.login'))

    try:
        with mysql.connection.cursor(MySQLdb.cursors.DictCursor) as cursor:
            cursor.execute("SELECT * FROM vacations WHERE id = %s", (id,))
            vacation = cursor.fetchone()

            if not vacation:
                flash("Vacation record not found", "danger")
                return redirect(url_for('vacations.vacations'))

            # Restore original employee in affected shifts
            cursor.execute("""
                UPDATE shifts
                SET employee_id = %s
                WHERE employee_id = %s
                  AND shift_date BETWEEN %s AND %s
            """, (
                vacation['employee_id'],
                vacation['substitute_id'],
                vacation['start_date'],
                vacation['end_date']
            ))

            cursor.execute("DELETE FROM vacations WHERE id = %s", (id,))

        mysql.connection.commit()
        flash("Vacation deleted successfully. Original assignments restored.", "success")

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error deleting vacation: {str(e)}", "danger")

    return redirect(url_for('vacations.vacations'))