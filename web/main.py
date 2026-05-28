from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import secrets
import sqlite3

app = Flask(__name__)
app.secret_key = 'my_easy_secret_key'

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Phrases table stays exactly the same
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
    
    # UPDATED: Users table now includes verification and token columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT,
            birthdate TEXT,
            japanese_level TEXT,
            is_verified INTEGER DEFAULT 0,
            reset_token TEXT,
            token_expiry TEXT
        )
    ''')

    # Global chat messages table stays exactly the same
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS global_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Profiles table stays exactly the same
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            email TEXT,
            japanese_level TEXT
        )
    ''')
    
    # --- FIX FOR EXISTING DATABASES ---
    # If your database file already exists on your computer, CREATE TABLE won't add new columns.
    # These lines below check if the columns exist, and add them if they are missing!
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass # Already exists!
        
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN reset_token TEXT")
    except sqlite3.OperationalError:
        pass # Already exists!

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN token_expiry TEXT")
    except sqlite3.OperationalError:
        pass # Already exists!
    # ----------------------------------

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
   
    username = session['user']
    
    # Fetch the user's email and Japanese level from the database using their username
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT email, japanese_level FROM users WHERE username = ?', (username,))
    user_data = cursor.fetchone()
    conn.close()
    
    # Set default values in case the database returns None (e.g., if email or japanese_level is NULL)
    email = "Not provided"
    japanese_level = "Not selected"
    
    if user_data:
        email = user_data[0] if user_data[0] else "Not provided"
        # Capitalize the Japanese level for better display, but only if it's not None or empty
        japanese_level = user_data[1].capitalize() if user_data[1] else "Not selected"

    # Pass the email and japanese_level variables into the profile.html template so they can be displayed on the page
    return render_template('profile.html', email=email, japanese_level=japanese_level)


@app.route('/global_chat', methods=['POST', 'GET'])
def global_chat():
    if 'user' not in session:
        flash('Please log in to participate in the global chat!', 'danger')
        return redirect(url_for('login_page'))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # IF USER SUBMITS A CHAT: Save it straight to the hard drive database
    if request.method == 'POST':
        message_text = request.form.get('message')
        if message_text and message_text.strip() != "":
            cursor.execute('INSERT INTO global_messages (username, message) VALUES (?, ?)', 
                           (session['user'], message_text))
            conn.commit()
            flash('Message posted successfully!', 'success') # Just a quick alert notification

            return redirect(url_for('global_chat'))
    
    #  EVERY TIME THE PAGE LOADS: Grab all historical messages from oldest to newest
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT username, message, datetime(timestamp, "localtime") FROM global_messages ORDER BY id ASC')
    db_messages = cursor.fetchall()
    conn.close()
    
    # Pass db_messages into our HTML template under the variable name 'messages'
    # Pass your database messages directly into your existing global_chat.html file
    return render_template('global_chat.html', messages=db_messages)

@app.route('/delete_chat', methods=['POST'])
def delete_chat():
    if 'user' not in session:
        return redirect(url_for('login_page'))
        
    msg_user = request.form.get('msg_user')
    msg_text = request.form.get('msg_text')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    #  This ensures users can ONLY delete their own messages!
    if session['user'] == msg_user:
        cursor.execute('DELETE FROM global_messages WHERE username = ? AND message = ?', (msg_user, msg_text))
        conn.commit()
        flash('Message deleted!', 'success')
    else:
        flash('You can only delete your own messages!', 'danger')
        
     
    conn.close()
    return redirect(url_for('global_chat'))


@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user' not in session:
        return redirect(url_for('login_page'))
    
    username = session['user']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Remove user account
    cursor.execute('DELETE FROM users WHERE username = ?', (username,))
    
    # Remove chats
    cursor.execute('DELETE FROM global_messages WHERE username = ?', (username,))
    
    conn.commit()
    conn.close()
    
    # Log out the user and clear their session data
    session.clear()
    
    flash('Your account has been permanently deleted.', 'success')
    return redirect(url_for('index'))


@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    email = request.form.get('email')
    birthdate = request.form.get('birthdate')
    japanese_level = request.form.get('japanese_level')

    
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
        cursor.execute('INSERT INTO users (username, password, email, birthdate, japanese_level) VALUES (?, ?, ?, ?, ?)', (username, password, email, birthdate, japanese_level))
        conn.commit()
        flash('Registration successful! Please log in below.', 'success')
        return redirect(url_for('login_page'))
    except sqlite3.IntegrityError:
        flash('That username is already taken. Try a different one.', 'danger')
        return redirect(url_for('register_page'))
    finally:
        conn.close()

@app.route('/check_username', methods=['POST'])
def check_username():
    data = request.get_json()
    username = data.get('username', '').strip()
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # This query checks if there's any record in the users table with the given username. If it finds one, it returns True; otherwise, False.
    cursor.execute('SELECT 1 FROM users WHERE username = ?', (username,))
    exists = cursor.fetchone() is not None
    conn.close()
    
    return jsonify({'exists': exists})


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
        return redirect(url_for('index'))
    else:
        flash('Invalid username or password.', 'danger')
        return redirect(url_for('login_page'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))

from flask_mail import Mail, Message

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'lhermans349@gmail.com'
app.config['MAIL_PASSWORD'] = 'qapi ztsq hatv gtdy'

mail = Mail(app)

@app.route('/test_email')
def test_email():
    try:
        # Create a simple test message
        msg = Message(
            subject="Hello from Phrase Manager!",
            sender=app.config['MAIL_USERNAME'],
            recipients=[app.config['MAIL_USERNAME']] # This sends it right back to yourself!
        )
        msg.body = "Hey there! If you are reading this, your Flask-Mail setup is working perfectly."
        
        # Actually send it
        mail.send(msg)
        return "Success! Check your Gmail inbox (and maybe your spam folder just in case)."
        
    except Exception as e:
        # If something breaks, it will show us the exact error message on the screen
        return f"Something went wrong: {str(e)}"
    
@app.route('/update_email', methods=['POST'])
def update_email():
    if 'user' not in session:
        flash('Please log in first!', 'danger')
        return redirect(url_for('login_page'))
        
    new_email = request.form.get('email').strip().lower()
    username = session['user']
    
    #  Generate a unique secure random token for the verification link
    verification_token = secrets.token_urlsafe(32)
    
    #  Update the database: Save the email, set is_verified to 0, save the token
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET email = ?, is_verified = 0, reset_token = ? 
        WHERE username = ?
    ''', (new_email, verification_token, username))
    conn.commit()
    conn.close()
    
    #  Create the unique click link pointing back to your website
    # _external=True turns it into a complete clickable web address (http://...)
    verify_url = url_for('verify_email', token=verification_token, _external=True)
    
    #  Fire off the real email via Gmail!
    try:
        msg = Message(
            subject="Verify Your New Email Address",
            sender=app.config['MAIL_USERNAME'],
            recipients=[new_email]
        )
        msg.body = f"Hello {username},\n\nYou requested to change or verify your email address. Please click the link below to confirm your email:\n\n{verify_url}\n\nIf you did not make this request, you can safely ignore this email."
        
        mail.send(msg)
        flash('Email updated successfully! Please check your inbox to verify it.', 'success')
    except Exception as e:
        flash(f'Email saved, but failed to send verification message: {str(e)}', 'danger')
        
    return redirect(url_for('profile'))


@app.route('/verify_email/<token>')
def verify_email(token):
    # Connect to your database
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Check if any user owns this exact security token
    cursor.execute('SELECT username FROM users WHERE reset_token = ?', (token,))
    user_row = cursor.fetchone()
    
    if user_row:
        username = user_row[0]
        
        # Match found! Turn is_verified to 1 (True) and clear out the token so it can't be reused
        cursor.execute('''
            UPDATE users 
            SET is_verified = 1, reset_token = NULL 
            WHERE username = ?
        ''', (username,))
        conn.commit()
        
        flash('Success! Your email address has been verified.', 'success')
    else:
        # If someone modifies the token string in the URL or uses an old link
        flash('Invalid or expired verification link.', 'danger')
        
    conn.close()
    
    # Send them back to their profile page to see the success message
    return redirect(url_for('profile'))

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