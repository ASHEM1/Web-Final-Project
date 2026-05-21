from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'my_easy_secret_key'

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Phrases now has user_id to isolate records per person
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS phrases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            japanese TEXT,
            romaji TEXT,
            english TEXT,
            category TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/phrases')
def phrases():
    return render_template('phrases.html')

@app.route('/characters')
def characters():
    return render_template('characters.html')

# Only fetches phrases matching the current logged-in user's ID
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash('Please log in first!', 'danger')
        return redirect(url_for('login_page'))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # First, find the numeric ID of the logged-in user
    cursor.execute('SELECT id FROM users WHERE username = ?', (session['user'],))
    user_row = cursor.fetchone()
    
    all_phrases = []
    if user_row:
        user_id = user_row[0]
        # Only select phrases where user_id matches this user
        cursor.execute('SELECT * FROM phrases WHERE user_id = ?', (user_id,))
        all_phrases = cursor.fetchall()
        
    conn.close()
    return render_template('dashboard.html', phrases=all_phrases)

@app.route('/login_page')
def login_page():
    return render_template('login.html')

@app.route('/register_page')
def register_page():
    return render_template('register.html')

@app.route('/profile')
def profile():
    if 'user' not in session:
        flash('Please log in first to view your profile!', 'danger')
        return redirect(url_for('login_page'))
    return render_template('profile.html')


@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if len(password) < 8:
        flash('Registration failed: Password must be at least 8 characters long.', 'danger')
        return redirect(url_for('register_page'))
        
    has_number = any(char.isdigit() for char in password)
    if not has_number:
        flash('Registration failed: Password must contain at least one number.', 'danger')
        return redirect(url_for('register_page'))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        flash('Registration successful! Please log in below.', 'success')
        return redirect(url_for('login_page'))
    except sqlite3.IntegrityError:
        flash('That username is already taken. Try a different one.', 'danger')
        return redirect(url_for('register_page'))
    finally:
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        session['user'] = username
        flash('Logged in successfully!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid username or password.', 'danger')
        return redirect(url_for('login_page'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/add_phrase', methods=['POST'])
def add_phrase():
    if 'user' not in session:
        return redirect(url_for('login_page'))

    japanese = request.form.get('japanese')
    romaji = request.form.get('romaji')
    english = request.form.get('english')
    category = request.form.get('category')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Find current user's ID to tag the new phrase row
    cursor.execute('SELECT id FROM users WHERE username = ?', (session['user'],))
    user_id = cursor.fetchone()[0]
    
    cursor.execute('INSERT INTO phrases (user_id, japanese, romaji, english, category) VALUES (?, ?, ?, ?, ?)', 
                   (user_id, japanese, romaji, english, category))
    conn.commit()
    conn.close()
    
    flash('New phrase added to your personal dictionary!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete_phrase/<int:phrase_id>')
def delete_phrase(phrase_id):
    if 'user' not in session:
        return redirect(url_for('login_page'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Security verification: Ensure this phrase actually belongs to the logged in user
    cursor.execute('SELECT id FROM users WHERE username = ?', (session['user'],))
    user_id = cursor.fetchone()[0]
    
    # Delete only if both phrase ID and user ID match
    cursor.execute('DELETE FROM phrases WHERE id = ? AND user_id = ?', (phrase_id, user_id))
    conn.commit()
    conn.close()
    
    flash('Phrase removed from your dictionary.', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)