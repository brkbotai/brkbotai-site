
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

users = {}

CSV_FILE = 'abonnements.csv'

def is_subscription_valid(email):
    if not os.path.exists(CSV_FILE):
        return False
    df = pd.read_csv(CSV_FILE)
    user = df[df['email'] == email]
    if user.empty:
        return False
    end_date = pd.to_datetime(user['date_fin'].values[0])
    return datetime.now() <= end_date

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email in users and check_password_hash(users[email], password):
            session['email'] = email
            return redirect(url_for('vip'))
        return "Identifiants incorrects"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm']
        if password != confirm:
            return "Les mots de passe ne correspondent pas"
        users[email] = generate_password_hash(password)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/vip')
def vip():
    if 'email' not in session:
        return redirect(url_for('login'))
    email = session['email']
    if not is_subscription_valid(email):
        return "Abonnement expiré ou non valide"
    return render_template('vip.html')

@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    ADMIN_EMAIL = "jamalassaki@hotmail.fr"
    if 'email' not in session or session['email'] != ADMIN_EMAIL:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'pdf' in request.files:
            pdf = request.files['pdf']
            if pdf.filename:
                pdf.save(os.path.join('static/files', 'top5.pdf'))

        if 'combine' in request.files:
            combine = request.files['combine']
            if combine.filename:
                combine.save(os.path.join('static/img', 'combine.jpg'))

        if 'fun' in request.files:
            fun = request.files['fun']
            if fun.filename:
                fun.save(os.path.join('static/img', 'fun.jpg'))

        return "Fichiers uploadés avec succès ! <a href='/upload'>Retour</a>"

    return render_template('upload.html')
