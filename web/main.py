from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3


app = Flask(__name__)
# The secret key is needed to keep user login sessions secure
app.secret_key = 'my_easy_secret_key'

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Create the phrases table (for our CRUD data)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS phrases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            japanese TEXT,
            romaji TEXT,
            english TEXT,
            category TEXT
        )
    ''')
    
    # Create the users table (stores usernames and simple passwords)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Run the database setup immediately when the app starts
init_db()


# Homepage (Getting Started)
@app.route('/')
def index():
    return render_template('index.html')

# Learning Phrases
@app.route('/phrases')
def phrases():
    return render_template('phrases.html')

# Writing Characters
@app.route('/characters')
def characters():
    return render_template('characters.html')

# Protected Dashboard (Only visible if logged in)
@app.route('/dashboard')
def dashboard():
    # Security Check: If 'user' is NOT in the session, kick them back to the home page
    if 'user' not in session:
        flash('Please log in first!', 'danger')
        return redirect(url_for('index'))
    
    # Fetch all phrases from the database to show in our table
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM phrases')
    all_phrases = cursor.fetchall()
    conn.close()
    
    # Send the phrases data into dashboard.html to be displayed
    return render_template('dashboard.html', phrases=all_phrases)

# Login Page
@app.route('/login_page')
def login_page():
    return render_template('login.html')

# Registration Page
@app.route('/register_page')
def register_page():
    return render_template('register.html')

# Secure User Profile Space
@app.route('/profile')
def profile():
    if 'user' not in session:
        flash('Please log in first to view your profile!', 'danger')
        return redirect(url_for('login_page'))
    return render_template('profile.html')



# USER ACCOUNT SYSTEM (LOGIN / REGISTER)

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    
    # --- Form Error Handling: Password Checks ---
    if len(password) < 8:
        flash('Registration failed: Password must be at least 8 characters long.', 'danger')
        return redirect(url_for('index'))
        
    # Check if password contains at least one number
    has_number = any(char.isdigit() for char in password)
    if not has_number:
        flash('Registration failed: Password must contain at least one number.', 'danger')
        return redirect(url_for('index'))
    
    # If the password passes checks, save the user to the database
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        flash('Registration successful! You can now log in.', 'success')
    except sqlite3.IntegrityError:
        # This error happens automatically if someone tries to pick a username that already exists
        flash('That username is already taken.', 'danger')
    finally:
        conn.close()
        
    return redirect(url_for('index'))


@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    # Search the database for this specific username and password
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        # Log the user in by saving their name into the temporary "session" cookie
        session['user'] = username
        flash('Logged in successfully!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid username or password.', 'danger')
        return redirect(url_for('index'))


@app.route('/logout')
def logout():
    # Remove the user from the session cookie
    session.pop('user', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))


# ADD & DELETE PHRASES

@app.route('/add_phrase', methods=['POST'])
def add_phrase():
    japanese = request.form.get('japanese')
    romaji = request.form.get('romaji')
    english = request.form.get('english')
    category = request.form.get('category')
    
    # Save the new phrase info into our SQLite database
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO phrases (japanese, romaji, english, category) VALUES (?, ?, ?, ?)', 
                   (japanese, romaji, english, category))
    conn.commit()
    conn.close()
    
    flash('New phrase added to your dictionary!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/delete_phrase/<int:phrase_id>')
def delete_phrase(phrase_id):
    # Find the specific phrase by its unique ID number and remove it
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM phrases WHERE id = ?', (phrase_id,))
    conn.commit()
    conn.close()
    
    flash('Phrase deleted.', 'success')
    return redirect(url_for('dashboard'))


# Start the local development web server
if __name__ == '__main__':
    app.run(debug=True)