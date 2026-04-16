from flask import Flask, render_template, request, redirect, url_for, session
import os
import mysql.connector

app = Flask(__name__)
# CRITICAL: Essential for Render to handle login sessions
app.secret_key = os.environ.get('SECRET_KEY', 'ccsu_bca_2026_premium_key')

def get_db_connection():
    # Use your existing environment variable or local config
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        return mysql.connector.connect(url=db_url)
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="yourpassword",
        database="library_db"
    )

@app.route('/')
def selection():
    return render_template('selection.html')

@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Demo Credentials
        if (role == 'admin' and username == 'admin' and password == 'admin123') or \
           (role == 'student' and username == 'student' and password == '12345'):
            
            session['role'] = role
            return redirect(url_for('dashboard_view'))
        
        return "Invalid Credentials. <a href='/'>Try again</a>"

    return render_template('login.html', role=role)

@app.route('/dashboard')
def dashboard_view():
    if 'role' not in session:
        return redirect(url_for('selection'))

    page = request.args.get('page', 1, type=int)
    per_page = 6
    offset = (page - 1) * per_page
    
    active_books = []
    total_active = 0
    issued_count = 0

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch Books
        cursor.execute("SELECT * FROM Books WHERE is_archived = FALSE LIMIT %s OFFSET %s", (per_page, offset))
        active_books = cursor.fetchall()

        # Fetch Total Count
        cursor.execute("SELECT COUNT(*) FROM Books WHERE is_archived = FALSE")
        total_active = cursor.fetchone()[0]

        # Fetch Issued Today
        cursor.execute("SELECT COUNT(*) FROM Issued_Books WHERE DATE(issue_date) = CURDATE()")
        issued_count = cursor.fetchone()[0]

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
        # Default fallback values so the page doesn't crash
        total_active = total_active or 0

    # Role-Based Context Logic
   if session.get('role') == 'admin':
    s2_label, s2_val = "Total Members", (850 if total_active > 0 else 0)
    s3_label, s3_val = "Issued Today", issued_count
else:
    s2_label, s2_val = "My Books", 0
    s3_label, s3_val = "Requests", 0

    return render_template(
        'index.html', 
        books=active_books, 
        total_count=total_active, 
        stat_2_label=s2_label, 
        stat_2_val=s2_val,
        stat_3_label=s3_label, 
        stat_3_val=s3_val,
        page=page,
        total_pages=(total_active // per_page) + 1,
        current_cat='All'
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('selection'))

if __name__ == '__main__':
    app.run(debug=True)
