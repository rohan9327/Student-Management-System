
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import os
import uuid
from database import get_db_connection, add_log

app = Flask(__name__)

app.secret_key = "student_project_secret"


# =====================================================
# PROFILE IMAGE SETTINGS
# =====================================================

UPLOAD_FOLDER = 'static/profile_pics'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):

    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# =====================================================
# LOGIN
# =====================================================

@app.route('/', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username'].strip()
        password = request.form['password']

        conn = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT username, password, role
                FROM public."Users"
                WHERE username = %s
            """, (username,))

            user = cursor.fetchone()

            if user and user[1] == password:

                session['username'] = user[0]
                session['role'] = user[2].lower()

                add_log(user[0], "Logged In Successfully")

                return redirect(url_for('dashboard'))

            return render_template(
                'login.html',
                error="Invalid Username or Password"
            )

        except Exception as e:

            print("Login Database Error:", e)

            return render_template(
                'login.html',
                error="Database Connection Failed"
            )

        finally:
            if conn:
                conn.close()

    return render_template('login.html')
# =====================================================
# DASHBOARD
# =====================================================

@app.route('/dashboard')
def dashboard():

    if 'username' not in session:
        return redirect(url_for('login'))

    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Total Students
cursor.execute('SELECT COUNT(*) FROM public."Students"')
total_students = cursor.fetchone()[0]

# Total Users
cursor.execute('SELECT COUNT(*) FROM public."Users"')
total_users = cursor.fetchone()[0]

# Today's Registrations
today = datetime.now().strftime('%d-%m-%Y')

cursor.execute("""
    SELECT COUNT(*)
    FROM public."Students"
    WHERE registration_date = %s
""", (today,))

today_registrations = cursor.fetchone()[0]

# Total Activities
cursor.execute('SELECT COUNT(*) FROM public."ActivityLogs"')
total_activities = cursor.fetchone()[0]

# Latest Activities
cursor.execute("""
    SELECT username, action, activity_date
    FROM public."ActivityLogs"
    ORDER BY id DESC
    LIMIT 10
""")

rows = cursor.fetchall()
        activity_logs = []

        for row in rows:

            activity_logs.append({
                'username': row[0],
                'action': row[1],
                'activity_date': row[2]
            })

        return render_template(
            'dashboard.html',
            total_students=total_students,
            total_users=total_users,
            today_registrations=today_registrations,
            total_activities=total_activities,
            activity_logs=activity_logs
        )

    except Exception as e:

        print("Dashboard Database Error:", e)
        flash("Unable to Load Dashboard Data!", "error")

        return redirect(url_for('login'))

    finally:

        if conn:
            conn.close()


# =====================================================
# ADD NEW USER
# =====================================================

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():

    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':

        username = request.form['username'].strip()
        password = request.form['password']
        role = request.form['role']

        if not username or not password:

            flash("All Fields Are Required!", "error")
            return redirect(url_for('add_user'))

        if role not in ['admin', 'user']:

            flash("Invalid User Role!", "error")
            return redirect(url_for('add_user'))

        conn = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id FROM Users
                WHERE username = ?
            """, (username,))

            if cursor.fetchone():

                flash("Username Already Exists!", "error")
                return redirect(url_for('add_user'))

            cursor.execute("""
                INSERT INTO Users (username, password, role)
                VALUES (?, ?, ?)
            """, (username, password, role))

            conn.commit()

            add_log(
                session['username'],
                f"Added new user: {username}"
            )

            flash("User Added Successfully!", "success")

            return redirect(url_for('add_user'))

        except Exception as e:

            if conn:
                conn.rollback()

            print("Database Error:", e)

            flash("Unable to Add User!", "error")

        finally:

            if conn:
                conn.close()

    return render_template('add_user.html')


# =====================================================
# MANAGE USERS
# =====================================================

@app.route('/manage_users')
def manage_users():

    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, username, role
            FROM Users
            ORDER BY id DESC
        """)

        rows = cursor.fetchall()

        users = []

        for row in rows:

            users.append({
                'id': row[0],
                'username': row[1],
                'role': row[2]
            })

        return render_template(
            'manage_users.html',
            users=users
        )

    except Exception as e:

        print("Database Error:", e)
        flash("Unable to Load Users!", "error")

        return render_template(
            'manage_users.html',
            users=[]
        )

    finally:

        if conn:
            conn.close()


# =====================================================
# EDIT USER
# =====================================================

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):

    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, username, role
            FROM Users
            WHERE id = ?
        """, (user_id,))

        row = cursor.fetchone()

        if row is None:

            flash("User Not Found!", "error")
            return redirect(url_for('manage_users'))

        selected_user = {
            'id': row[0],
            'username': row[1],
            'role': row[2]
        }

        if request.method == 'POST':

            new_username = request.form['username'].strip()
            new_password = request.form['password']
            new_role = request.form['role']

            if not new_username:

                flash("Username is Required!", "error")
                return redirect(url_for('edit_user', user_id=user_id))

            if new_role not in ['admin', 'user']:

                flash("Invalid User Role!", "error")
                return redirect(url_for('edit_user', user_id=user_id))

            cursor.execute("""
                SELECT id FROM Users
                WHERE username = ? AND id != ?
            """, (new_username, user_id))

            if cursor.fetchone():

                flash("Username Already Exists!", "error")
                return redirect(url_for('edit_user', user_id=user_id))

            if new_password:

                cursor.execute("""
                    UPDATE Users
                    SET username = ?, password = ?, role = ?
                    WHERE id = ?
                """, (new_username, new_password, new_role, user_id))

            else:

                cursor.execute("""
                    UPDATE Users
                    SET username = ?, role = ?
                    WHERE id = ?
                """, (new_username, new_role, user_id))

            conn.commit()

            add_log(
                session['username'],
                f"Updated user: {new_username}"
            )

            flash("User Updated Successfully!", "success")

            return redirect(url_for('manage_users'))

        return render_template(
            'edit_user.html',
            user=selected_user
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print("Database Error:", e)
        flash("Unable to Update User!", "error")

        return redirect(url_for('manage_users'))

    finally:

        if conn:
            conn.close()


# =====================================================
# DELETE USER
# =====================================================

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):

    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT username
            FROM Users
            WHERE id = ?
        """, (user_id,))

        row = cursor.fetchone()

        if row is None:

            flash("User Not Found!", "error")
            return redirect(url_for('manage_users'))

        username_to_delete = row[0]

        if username_to_delete == session['username']:

            flash("You cannot delete your own account!", "error")
            return redirect(url_for('manage_users'))

        cursor.execute("""
            DELETE FROM Users
            WHERE id = ?
        """, (user_id,))

        conn.commit()

        add_log(
            session['username'],
            f"Deleted user: {username_to_delete}"
        )

        flash("User Deleted Successfully!", "success")

    except Exception as e:

        if conn:
            conn.rollback()

        print("Database Error:", e)
        flash("Unable to Delete User!", "error")

    finally:

        if conn:
            conn.close()

    return redirect(url_for('manage_users'))


# =====================================================
# STUDENT REGISTRATION
# =====================================================

@app.route('/register', methods=['GET', 'POST'])
def register():

    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':

        name = request.form['student_name']
        course = request.form['student_course']
        age = int(request.form['student_age'])
        city = request.form['student_city']
        phone = request.form['student_phone']
        email = request.form['student_email']

        registration_date = datetime.now().strftime('%d-%m-%Y')

        conn = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO Students
                (name, course, age, city, phone, email, registration_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                course,
                age,
                city,
                phone,
                email,
                registration_date
            ))

            conn.commit()

            add_log(
                session['username'],
                f"Added Student: {name}"
            )

            flash("Student Added Successfully!", "success")

            return redirect(url_for('view_students'))

        except Exception as e:

            if conn:
                conn.rollback()

            print("Student Registration Error:", e)

            return f"Database Error: {e}"

        finally:

            if conn:
                conn.close()

    return render_template('add_student.html')


# =====================================================
# VIEW STUDENTS
# =====================================================

@app.route('/view_students')
def view_students():

    if 'username' not in session:
        return redirect(url_for('login'))

    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM Students
            ORDER BY id DESC
        """)

        students = cursor.fetchall()

        return render_template(
            'view_students.html',
            students=students
        )

    except Exception as e:

        print("View Students Error:", e)

        return f"Database Error: {e}"

    finally:

        if conn:
            conn.close()


# =====================================================
# EDIT STUDENT
# =====================================================

@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):

    if 'username' not in session:
        return redirect(url_for('login'))

    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == 'POST':

            name = request.form['name']
            age = int(request.form['age'])
            city = request.form['city']
            phone = request.form['phone']
            email = request.form['email']
            course = request.form['course']

            cursor.execute("""
                UPDATE Students
                SET name = ?,
                    age = ?,
                    city = ?,
                    phone = ?,
                    email = ?,
                    course = ?
                WHERE id = ?
            """, (
                name,
                age,
                city,
                phone,
                email,
                course,
                student_id
            ))

            if cursor.rowcount == 0:

                flash("Student Not Found!", "error")
                return redirect(url_for('view_students'))

            conn.commit()

            add_log(
                session['username'],
                f"Updated Student: {name} (ID: {student_id})"
            )

            flash("Student Updated Successfully!", "success")

            return redirect(url_for('view_students'))

        cursor.execute("""
            SELECT *
            FROM Students
            WHERE id = ?
        """, (student_id,))

        student = cursor.fetchone()

        if student is None:

            flash("Student Not Found!", "error")
            return redirect(url_for('view_students'))

        return render_template(
            'edit_student.html',
            student=student
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print("Edit Student Error:", e)

        return f"Database Error: {e}"

    finally:

        if conn:
            conn.close()


# =====================================================
# DELETE STUDENT
# =====================================================

@app.route('/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):

    if 'username' not in session:
        return redirect(url_for('login'))

    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name
            FROM Students
            WHERE id = ?
        """, (student_id,))

        student = cursor.fetchone()

        if student:

            student_name = student[0]

            cursor.execute("""
                DELETE FROM Students
                WHERE id = ?
            """, (student_id,))

            conn.commit()

            add_log(
                session['username'],
                f"Deleted Student: {student_name} (ID: {student_id})"
            )

            flash("Student Deleted Successfully!", "success")

        else:

            flash("Student Not Found!", "error")

    except Exception as e:

        if conn:
            conn.rollback()

        print("Delete Student Error:", e)

        flash(f"Database Error: {e}", "error")

    finally:

        if conn:
            conn.close()

    return redirect(url_for('view_students'))


# =====================================================
# ACTIVITY LOGS
# =====================================================

@app.route('/logs')
def logs():

    if 'username' not in session:
        return redirect(url_for('login'))

    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT username, action, activity_date
            FROM ActivityLogs
            ORDER BY id DESC
        """)

        rows = cursor.fetchall()

        activity_logs = []

        for row in rows:

            activity_logs.append({
                'username': row[0],
                'action': row[1],
                'time': row[2].strftime('%d-%m-%Y %I:%M %p')
                if row[2] else ''
            })

        return render_template(
            'logs.html',
            activity_logs=activity_logs
        )

    except Exception as e:

        print("Activity Logs Database Error:", e)

        flash("Unable to Load Activity Logs!", "error")

        return render_template(
            'logs.html',
            activity_logs=[]
        )

    finally:

        if conn:
            conn.close()


# =====================================================
# REPORTS
# =====================================================

@app.route('/reports')
def reports():

    if 'username' not in session:
        return redirect(url_for('login'))

    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Total Students
        cursor.execute("SELECT COUNT(*) FROM Students")
        total_students = cursor.fetchone()[0]

        # All Students
        cursor.execute("SELECT * FROM Students")

        student_rows = cursor.fetchall()

        student_columns = [
            column[0] for column in cursor.description
        ]

        students = [
            dict(zip(student_columns, row))
            for row in student_rows
        ]

        # Total Users
        cursor.execute("SELECT COUNT(*) FROM Users")
        total_users = cursor.fetchone()[0]

        # All Users
        cursor.execute("""
            SELECT id, username, role
            FROM Users
            ORDER BY id DESC
        """)

        user_rows = cursor.fetchall()

        users = [
            {
                'id': row[0],
                'username': row[1],
                'role': row[2]
            }
            for row in user_rows
        ]

        # Today's Registrations
        today = datetime.now().strftime('%d-%m-%Y')

        cursor.execute("""
            SELECT COUNT(*)
            FROM Students
            WHERE registration_date = ?
        """, (today,))

        today_registrations = cursor.fetchone()[0]

        # Total Activities
        cursor.execute("SELECT COUNT(*) FROM ActivityLogs")
        total_activities = cursor.fetchone()[0]

        # Latest Activities
        cursor.execute("""
            SELECT username, action, activity_date
            FROM ActivityLogs
            ORDER BY id DESC
        """)

        activity_rows = cursor.fetchall()

        activity_logs = []

        for row in activity_rows:

            activity_logs.append({
                'username': row[0],
                'action': row[1],
                'time': row[2].strftime('%d-%m-%Y %I:%M %p')
                if row[2] else ''
            })

        return render_template(
            'reports.html',
            students=students,
            users=users,
            activity_logs=activity_logs,
            total_students=total_students,
            total_users=total_users,
            today_registrations=today_registrations,
            total_activities=total_activities,
            today=today
        )

    except Exception as e:

        print("Reports Database Error:", e)

        flash("Unable to Load Reports!", "error")

        return redirect(url_for('dashboard'))

    finally:

        if conn:
            conn.close()


# =====================================================
# MY PROFILE
# =====================================================

@app.route('/my_profile', methods=['GET', 'POST'])
def my_profile():

    if 'username' not in session:
        return redirect(url_for('login'))

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, username, password, role,
                   name, email, phone, profile_pic
            FROM Users
            WHERE username = ?
        """, (session['username'],))

        row = cursor.fetchone()

        if row is None:

            session.clear()
            return redirect(url_for('login'))

        current_user = {
            'id': row[0],
            'username': row[1],
            'password': row[2],
            'role': row[3],
            'name': row[4] or '',
            'email': row[5] or '',
            'phone': row[6] or '',
            'profile_pic': row[7] or ''
        }

        if request.method == 'POST':

            new_username = request.form.get('username', '').strip()
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            new_password = request.form.get('password', '')

            if not new_username or not name:

                flash("Username and Name are required!", "error")

                return redirect(url_for('my_profile'))

            cursor.execute("""
                SELECT id
                FROM Users
                WHERE username = ? AND id != ?
            """, (new_username, current_user['id']))

            if cursor.fetchone():

                flash("Username Already Exists!", "error")

                return redirect(url_for('my_profile'))

            password = (
                new_password
                if new_password
                else current_user['password']
            )

            # Profile Picture Upload
            file = request.files.get('profile_pic')

            profile_pic = current_user['profile_pic']

            if file and file.filename:

                if not allowed_file(file.filename):

                    flash(
                        "Only JPG, JPEG and PNG files are allowed!",
                        "error"
                    )

                    return redirect(url_for('my_profile'))

                extension = file.filename.rsplit('.', 1)[1].lower()

                filename = str(uuid.uuid4()) + '.' + extension

                file.save(
                    os.path.join(
                        app.config['UPLOAD_FOLDER'],
                        filename
                    )
                )

                profile_pic = filename

            # Update User
            cursor.execute("""
                UPDATE Users
                SET username = ?,
                    password = ?,
                    name = ?,
                    email = ?,
                    phone = ?,
                    profile_pic = ?
                WHERE id = ?
            """, (
                new_username,
                password,
                name,
                email,
                phone,
                profile_pic,
                current_user['id']
            ))

            conn.commit()

            # Update Session
            session['username'] = new_username

            # Activity Log
            add_log(
                new_username,
                "Updated Own Profile"
            )

            flash("Profile Updated Successfully!", "success")

            return redirect(url_for('my_profile'))

        return render_template(
            'my_profile.html',
            user=current_user
        )

    except Exception as e:

        if conn:
            conn.rollback()

        print("My Profile Error:", e)

        flash(f"Database Error: {e}", "error")

        return redirect(url_for('dashboard'))

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =====================================================
# LOGOUT
# =====================================================

@app.route('/logout')
def logout():

    if 'username' in session:

        add_log(
            session['username'],
            "Logged Out Successfully"
        )

    session.clear()

    return redirect(url_for('login'))


# =====================================================
# RUN APPLICATION
# =====================================================

if __name__ == '__main__':

    app.run(debug=True)
