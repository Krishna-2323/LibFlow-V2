import os
import psycopg2 
import mysql.connector 
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
app.secret_key = 'ccsu_project_secret' # This allows Flask to use sessions

def get_db_connection():
    db_url = os.environ.get('DATABASE_URL') 
    if db_url:
        return psycopg2.connect(db_url)
    else:
        return mysql.connector.connect(
            host="127.0.0.1",
            user="root",
            password="",
            database="library_db"
        )

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Books (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                author VARCHAR(255) NOT NULL,
                category VARCHAR(100),
                is_archived BOOLEAN DEFAULT FALSE
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Issued_Books (
                id SERIAL PRIMARY KEY,
                book_id INT,
                member_name VARCHAR(255),
                issue_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES Books(id)
            );
        """)
        conn.commit()
    finally:
        cursor.close()
        conn.close()

init_db()

@app.route('/dashboard')
def index():
    if 'role' not in session:
        return redirect(url_for('selection'))
    page = request.args.get('page', 1, type=int)
    selected_cat = request.args.get('cat', 'All') 
    per_page = 6
    offset = (page - 1) * per_page

    active_books, archived_books = [], []
    total_active, issued_count, total_pages = 0, 0, 1

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if selected_cat == 'All':
            query = "SELECT * FROM Books WHERE is_archived = FALSE ORDER BY id ASC LIMIT %s OFFSET %s"
            params = (per_page, offset)
            count_query = "SELECT COUNT(*) FROM Books WHERE is_archived = FALSE"
            count_params = ()
        else:
            query = "SELECT * FROM Books WHERE is_archived = FALSE AND category LIKE %s ORDER BY id ASC LIMIT %s OFFSET %s"
            params = (f"%{selected_cat}%", per_page, offset)
            count_query = "SELECT COUNT(*) FROM Books WHERE is_archived = FALSE AND category LIKE %s"
            count_params = (f"%{selected_cat}%",)

        cursor.execute(query, params)
        active_books = cursor.fetchall()
        cursor.execute(count_query, count_params)
        total_active = cursor.fetchone()[0]
        total_pages = (total_active + per_page - 1) // per_page if total_active > 0 else 1

        cursor.execute("SELECT * FROM Books WHERE is_archived = TRUE ORDER BY id DESC")
        archived_books = cursor.fetchall()

        if os.environ.get('DATABASE_URL'):
            cursor.execute("SELECT COUNT(*) FROM Issued_Books WHERE DATE(issue_date) = CURRENT_DATE")
        else:
            cursor.execute("SELECT COUNT(*) FROM Issued_Books WHERE DATE(issue_date) = CURDATE()")
        issued_count = cursor.fetchone()[0]

    finally:
        cursor.close()
        conn.close()

    return render_template('index.html', books=active_books, archived=archived_books, total_count=total_active, page=page, total_pages=total_pages, current_cat=selected_cat, issued_today=issued_count)

@app.route('/add', methods=['POST'])
def add_book():
    title = request.form.get('title')
    author = request.form.get('author')
    cat = request.form.get('category')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Books (title, author, category, is_archived) VALUES (%s, %s, %s, FALSE)", (title, author, cat))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('index'))

@app.route('/archive/<int:id>')
def archive_book(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Books SET is_archived = TRUE WHERE id = %s", (id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('index'))

@app.route('/restore/<int:id>')
def restore_book(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Books SET is_archived = FALSE WHERE id = %s", (id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def permanent_delete(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Books WHERE id = %s", (id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('index'))

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('search_query')
    return redirect(url_for('index', cat=query))
    
@app.route('/')
def selection():
    return render_template('selection.html')
    
@app.route('/logout')
def logout():
    session.clear() # Clears role and user_id
    return redirect(url_for('selection'))
    
@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Simple check for your presentation
        if role == 'admin' and username == 'admin' and password == 'admin123':
            session['role'] = 'admin'
            return redirect(url_for('index'))
        
        elif role == 'student' and username == 'student' and password == '12345':
            session['role'] = 'student'
            return redirect(url_for('index'))
        
        else:
            return "Invalid Credentials. Try admin/admin123 or student/12345"

    return render_template('login.html', role=role)
if __name__ == '__main__':
    app.run()
