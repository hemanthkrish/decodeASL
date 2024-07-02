from flask import Flask, render_template, request, jsonify,redirect,url_for
import os
from PIL import Image, ImageSequence
# nltk imports
import re
from nltk.tokenize import word_tokenize

# game extra imports
import random
# login feature imports
from flask import session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)

# login variables start
app.secret_key = os.urandom(24)  # Secret key for session management

# Function to connect to SQLite database
def connect_db():
    conn = sqlite3.connect('database.db')
    return conn

# Create users table if it does not exist
def init_db():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            salt TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# login variables end


# game varibles start
# Path to the folder containing images
IMAGE_FOLDER = 'static/images/'

# List of image filenames
image_files = os.listdir(IMAGE_FOLDER)

# Shuffle the list to randomize image order
random.shuffle(image_files)

# Track current image index and user score
current_index = 0
score = 0
feedback = None  # Variable to store correct/wrong feedback

# game variabes end

def create_gif_from_images(image_names, output_path):
    images = []
    for img_name in image_names:
        img_path = os.path.join('static', 'images', img_name + '.jpg')  # Assuming images are JPEG format
        if os.path.exists(img_path):
            img = Image.open(img_path)
            images.append(img)

    if images:
        images[0].save(output_path, save_all=True, append_images=images[1:], loop=0, duration=1000)

def get_gif_duration(gif_path):
    with Image.open(gif_path) as img:
        gif_duration = 0
        for frame in ImageSequence.Iterator(img):
            try:
                gif_duration += frame.info['duration']
            except KeyError:
                # If the 'duration' key is not present in frame.info, use a default duration (100 milliseconds)
                gif_duration += 100
    return gif_duration

# nltk function to convert the givent text without punctuation
def preprocess_text(text):
    # Convert text to lowercase
    text = text.lower()
    # Remove punctuation using regular expression
    text = re.sub(r'[^\w\s]', '', text)
    # Tokenize the text into words
    words = word_tokenize(text)
    return words

@app.route('/search_gif', methods=['POST'])
def search_gif():
    # words = request.form['words'].split()
    words = preprocess_text(request.form['words'])

    gifs_info = []
    for word in words:
        gif_path = os.path.join('static', 'images', word + '.gif')
        if os.path.exists(gif_path):
            duration = get_gif_duration(gif_path)
            gifs_info.append({'path': gif_path, 'duration': duration})
        else:
            create_gif_from_images(list(word), gif_path)
            duration = len(word) * 1000  # Duration set to 1000 * number of letters in the word
            gifs_info.append({'path': gif_path, 'duration': duration})

    return render_template('replay_auto.html', gifs_info=gifs_info)

@app.route('/')
def index():
    if 'logged_in' in session:
        return render_template('index.html', username=session['username'])
    else:
        return redirect(url_for('login'))
    # return render_template("index.html")

# game routes
@app.route('/game')
def game():
    
    
    if 'logged_in' in session:
        global current_index, score, feedback
        if current_index < len(image_files): # add a number so you can stop some where
            # Get the current image filename
            image_filename = image_files[current_index]
            return render_template('game.html', image_filename=image_filename, score=score, feedback=feedback, num_images=len(image_files))
        else:
            return render_template('game_over.html', score=score)
        
    else:
        flash('Please log in to access this page.')
        return redirect(url_for('login'))
    
    

@app.route('/check_answer', methods=['POST'])
def check_answer():
    global current_index, score, feedback
    user_answer = request.form['user_answer']
    correct_answer = image_files[current_index].split('.')[0]
    feedback = "Correct!" if user_answer.lower() == correct_answer.lower() else "Wrong!"
    if user_answer.lower() == correct_answer.lower():
        score += 1
    current_index += 1
    return redirect(url_for('game'))
# game routes end

# login routes start
# Route for user registration
# Route for user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Generate salt
        salt = str(os.urandom(16))
        # Hash the password with salt
        hashed_password = generate_password_hash(password + salt)

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (username, password, salt) VALUES (?, ?, ?)', (username, hashed_password, salt))
        conn.commit()
        conn.close()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')


# Route for user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username=?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user:
            hashed_password = user[2]
            salt = user[3]  # Fetch the salt value from the database
            if check_password_hash(hashed_password, password + salt):
                session['logged_in'] = True
                session['username'] = username
                flash('Login successful!')
                
                return redirect('/')
            
        flash('Invalid username or password!')
    return render_template('login.html')

# Route for user logout
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('You have been logged out.')
    return redirect(url_for('login'))

@app.before_request
def require_login():
    allowed_routes = ['login', 'register']  # Routes that do not require login
    if request.endpoint not in allowed_routes and 'logged_in' not in session:
        return redirect(url_for('login'))
# login routes end



if __name__ == '__main__':
    app.run(debug=True)
