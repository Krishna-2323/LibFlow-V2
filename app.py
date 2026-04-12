import os
import psycopg2 # For Render
import mysql.connector # For your Laptop (XAMPP)

def get_db_connection():
    # If we are on Render, use the Database URL they provide
    # If we are on your laptop, use the Localhost settings
    db_url = os.environ.get('DATABASE_URL') 
    
    if db_url:
        # This is for the LIVE website
        return psycopg2.connect(db_url)
    else:
        # This is for your LOCAL testing (XAMPP)
        return mysql.connector.connect(
            host="127.0.0.1",
            user="root",
            password="",
            database="library_db"
        )

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    # Get the selected category from the URL
    selected_cat = request.args.get('cat', 'All') 
    per_page = 6
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor()

    # Logic to filter by category
    if selected_cat == 'All':
        query = "SELECT * FROM Books WHERE is_archived = FALSE ORDER BY id ASC LIMIT %s OFFSET %s"
        params = (per_page, offset)
        count_query = "SELECT COUNT(*) FROM Books WHERE is_archived = FALSE"
        count_params = ()
    else:
        # Matches Hindi, School, or BCA categories
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

    cursor.execute("SELECT COUNT(*) FROM Issued_Books WHERE DATE(issue_date) = CURDATE()")
    issued_count = cursor.fetchone()[0]
     
    cursor.close()
    conn.close()

    return render_template('index.html', 
                           books=active_books, 
                           archived=archived_books, 
                           total_count=total_active, 
                           page=page, 
                           total_pages=total_pages, 
                           current_cat=selected_cat,
                           issued_today=issued_count)

@app.route('/add', methods=['POST'])
def add_book():
    title, author, cat = request.form.get('title'), request.form.get('author'), request.form.get('category')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Books (title, author, category, is_archived) VALUES (%s, %s, %s, FALSE)", (title, author, cat))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/archive/<int:id>')
def archive_book(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Books SET is_archived = TRUE WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/issue', methods=['POST'])
def issue_book():
    book_id = request.form.get('book_id')
    member = request.form.get('member_name')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Issued_Books (book_id, member_name) VALUES (%s, %s)", (book_id, member))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))
if __name__ == '__main__': app.run()