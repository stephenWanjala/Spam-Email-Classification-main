import os
import pickle
import string

import mysql.connector
import nltk

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash
from nltk.stem import PorterStemmer

# Load environment variables from .env file
load_dotenv()

# Accessing environment variables
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
SECRET_KEY = os.getenv("SECRET_KEY")
app = Flask(__name__)
app.secret_key = SECRET_KEY

ps = PorterStemmer()
tfidf = pickle.load(open('vectorizer.pkl', 'rb'))
model = pickle.load(open('model.pkl', 'rb'))

nltk.download('punkt')


def transform_text(text):
    text = text.lower()
    text = nltk.word_tokenize(text)

    y = []
    for i in text:
        if i.isalnum():
            y.append(i)

    text = y[:]
    y.clear()

    for i in text:
        if i not in string.punctuation:
            y.append(i)

    text = y[:]
    y.clear()

    for i in text:
        y.append(ps.stem(i))

    return " ".join(y)


# Define your database connection
db = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME
)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/index')
def index():
    # Check if the 'user' session variable exists (i.e., the user is logged in)
    if 'user' in session:
        return render_template('index.html')
    else:
        return redirect(url_for('signin'))  # Redirect to the sign-in page if the user is not logged in


@app.route('/predict', methods=['POST'])
def predict():
    input_sms = request.form.get('message')
    transformed_sms = transform_text(input_sms)
    vector_input = tfidf.transform([transformed_sms])
    result = model.predict(vector_input)[0]
    if result == 1:
        prediction = "Spam"
    else:
        prediction = "Not Spam"
    return render_template('result.html', prediction=prediction)


@app.route('/signin')
def signin():
    if 'user' in session:
        return redirect(url_for('index'))
    return render_template('signin.html')


@app.route('/signup', methods=['GET'])
def signup():
    return render_template('signup.html')


@app.route('/register', methods=['POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        # Ensure the password and confirm_password match
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            return "Password and Confirm Password do not match."

        # Insert data into MySQL
        cur = db.cursor()
        cur.execute("INSERT INTO users (full_name, username, email, phone, password) VALUES (%s, %s, %s, %s, %s)",
                    (full_name, username, email, phone, password))
        db.commit()
        cur.close()

        flash('Registration successful', 'success')
        return redirect('/signin')

    return "Invalid request method"


@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember_me = request.form.get('remember_me')  # Get the 'remember_me' checkbox value

        # Query the database to check if the email and password match
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        user = cur.fetchone()
        cur.close()

        if user:
            session['user'] = user

            if remember_me:
                session.permanent = True
            return redirect(url_for('index'))
        else:
            return "Login failed. Check your email and password."

    return "Invalid request method"


@app.route('/logout')
def logout():
    # Clear the user session to log out
    session.pop('user', None)
    return redirect(url_for('home'))  # Redirect to the sign-in page after logging out


if __name__ == '__main__':
    app.run(debug=True)
