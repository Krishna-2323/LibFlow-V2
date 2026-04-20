from flask import Flask, render_template, request, redirect, url_for, session
import os
import mysql.connector

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ccsu_bca_2026_premium_key')

def get_db_connection():
    # Priority: Environment variable for deployment, else local config
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        # Note: mysql.connector.connect(url=...) is a placeholder; 
        # normally you'd parse a URI or use separate env vars for Host/User/Pass
        return mysql.connector.connect(host=os.environ.get('DB_HOST'))
        
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
    total_members = 0

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Fetch Active Books (is_archived = 0)
        cursor.execute("SELECT * FROM Books WHERE is_archived = FALSE LIMIT %s OFFSET %s", (per_page, offset))
        active_books = cursor.fetchall()

        # 2. Total Active Books Count
        cursor.execute("SELECT COUNT(*) FROM Books WHERE is_archived = FALSE")
        total_active = cursor.fetchone()[0]

        # 3. Issued Today Count
        cursor.execute("SELECT COUNT(*) FROM Issued_Books WHERE DATE(issue_date) = CURDATE()")
        issued_count = cursor.fetchone()[0]

        # 4. Total Members (assuming you have a 'Users' table)
        # cursor.execute("SELECT COUNT(*) FROM Users WHERE role = 'student'")
        # total_members = cursor.fetchone()[0]
        total_members = 85 # Hardcoded fallback if Users table isn't ready

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

    # Dynamic Stats logic for the 4 dashboard cards
    if session.get('role') == 'admin':
        s2_label, s2_val = "Total Members", total_members
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
        total_pages=(total_active // per_page) + 1
    )

# --- NEW: ARCHIVE LOGIC ---

@app.route('/archive/<int:id>')
def archive_book(id):
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard_view'))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Set is_archived to True instead of deleting the row
        cursor.execute("UPDATE Books SET is_archived = TRUE WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Archive error: {e}")
        
    return redirect(url_for('dashboard_view'))

@app.route('/vault')
def archive_vault():
    if 'role' not in session:
        return redirect(url_for('selection'))
    
    archived_books = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Books WHERE is_archived = TRUE")
        archived_books = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Vault error: {e}")

    return render_template('archive.html', books=archived_books)

@app.route('/add', methods=['POST'])
def add_book():
    if session.get('role') == 'admin':
        title = request.form.get('title')
        author = request.form.get('author')
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Books (title, author, is_archived) VALUES (%s, %s, FALSE)", (title, author))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Add error: {e}")
    return redirect(url_for('dashboard_view'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('selection'))

if __name__ == '__main__':
    app.run(debug=True)
