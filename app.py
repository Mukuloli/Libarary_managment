from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from pymysql.cursors import DictCursor
import pymysql
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Replace with your own secret key

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

            # Membership table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memberships (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    type ENUM('6 months', '1 year', '2 years') DEFAULT '6 months',
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
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

# Return Book
@app.route('/return_book', methods=['POST'])
def return_book():
    book_id = request.form['book_id']
    serial_no = request.form['serial_no']

    if not book_id or not serial_no:
        flash('Book ID and Serial No. are required.', 'danger')
        return redirect(url_for('user_dashboard'))

    # Logic for calculating fines (if needed)

    flash('Book returned successfully!', 'success')
    return redirect(url_for('user_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
