from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from pymysql.cursors import DictCursor
import pymysql
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "supersecretkey"  

# Database connection
def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',
        db='library_management',
        cursorclass=DictCursor
    )
def create_tables():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Users table for my Userhtml page
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    role ENUM('admin', 'user') NOT NULL
                );
            """)

            # Books table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    author VARCHAR(255) NOT NULL,
                    available BOOLEAN DEFAULT TRUE
                );
            """)

            # Issued Books table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS issued_books (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    book_id INT NOT NULL,
                    user_id INT NOT NULL,
                    issue_date DATE NOT NULL,
                    return_date DATE NOT NULL,
                    FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                );
            """)

            # Fines table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fines (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    issue_id INT NOT NULL,
                    fine_amount DECIMAL(10, 2) DEFAULT 0.00,
                    paid BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (issue_id) REFERENCES issued_books (id) ON DELETE CASCADE
                );
            """)

            
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS return_books (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    issue_id INT NOT NULL,
                    return_date DATE NOT NULL,
                    fine_amount DECIMAL(10, 2) DEFAULT 0.00,
                    FOREIGN KEY (issue_id) REFERENCES issued_books (id) ON DELETE CASCADE
                );
            """)

            connection.commit()
            print("All tables created successfully.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        connection.close()
create_tables()

# Home page
@app.route('/')
def home():
    return render_template('login.html')

# User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)", 
                           (username, generate_password_hash(password), role))
        connection.commit()
        connection.close()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('home'))

    return render_template('register.html')

# Login
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
    connection.close()

    if user and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['id']
        session['role'] = user['role']
        session['username'] = user['username']
        flash('Login successful!', 'success')

        if user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    else:
        flash('Invalid username or password', 'danger')
        return redirect(url_for('home'))

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

# Admin Dashboard
@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    return render_template('dashboard.html', role='admin')

# User Dashboard
@app.route('/user_dashboard')
def user_dashboard():
    if session.get('role') != 'user':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    return render_template('dashboard.html', role='user')

# Add Book
@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if session.get('role') != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']

        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO books (title, author) VALUES (%s, %s)", (title, author))
        connection.commit()
        connection.close()

        flash('Book added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_book.html')

# Issue Book
@app.route('/issue_book', methods=['GET', 'POST'])
def issue_book():
    if request.method == 'POST':
        book_id = request.form['book_id']
        user_id = request.form['user_id']
        issue_date = datetime.now().strftime('%Y-%m-%d')
        return_date = (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d')

        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO issued_books (book_id, user_id, issue_date, return_date) VALUES (%s, %s, %s, %s)",
                           (book_id, user_id, issue_date, return_date))
        connection.commit()
        connection.close()

        flash('Book issued successfully!', 'success')
        return redirect(url_for('user_dashboard'))

    return render_template('issue_book.html')
@app.route('/return_book', methods=['GET', 'POST'])
def return_book():
    if request.method == 'POST':
        book_id = request.form['book_id']
        user_id = session.get('user_id')

        if not book_id:
            flash('Book ID is required.', 'danger')
            return redirect(url_for('user_dashboard'))

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                
                cursor.execute("""
                    SELECT id, return_date 
                    FROM issued_books 
                    WHERE book_id = %s AND user_id = %s
                """, (book_id, user_id))
                issued_book = cursor.fetchone()

                if not issued_book:
                    flash('No matching issued book found.', 'danger')
                    return redirect(url_for('user_dashboard'))

                
                today = datetime.now().date()
                fine_amount = 0.00
                if today > issued_book['return_date']:
                    overdue_days = (today - issued_book['return_date']).days
                    fine_amount = overdue_days * 2  

                
                cursor.execute("""
                    INSERT INTO return_books (issue_id, return_date, fine_amount) 
                    VALUES (%s, %s, %s)
                """, (issued_book['id'], today, fine_amount))

                
                cursor.execute("UPDATE books SET available = TRUE WHERE id = %s", (book_id,))

            connection.commit()

            if fine_amount > 0:
                flash(f'Book returned successfully! Fine incurred: ${fine_amount:.2f}', 'warning')
            else:
                flash('Book returned successfully!', 'success')
        except Exception as e:
            connection.rollback()
            flash(f'Error returning book: {e}', 'danger')
        finally:
            connection.close()

        return redirect(url_for('user_dashboard'))

    return render_template('return_book.html')


if __name__ == '__main__':
    app.run(debug=True)
