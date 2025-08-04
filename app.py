
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import json
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

ABONNEMENTS_FILE = 'abonnements.json'

def load_abonnements():
    try:
        with open(ABONNEMENTS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def is_subscription_valid(email):
    abonnements = load_abonnements()
    today = datetime.today().date()
    for ab in abonnements:
        if ab['email'] == email:
            date_fin = datetime.strptime(ab['date_fin'], '%Y-%m-%d').date()
            return date_fin >= today
    return False

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['email'] = request.form['email']
        return redirect(url_for('vip'))
    return render_template("login.html")

@app.route('/vip')
def vip():
    if 'email' not in session:
        return redirect(url_for('login'))
    if not is_subscription_valid(session['email']):
        return "Abonnement expiré ou non valide."
    return render_template("vip.html")

@app.route('/add_abonne', methods=['GET', 'POST'])
def add_abonne():
    if 'email' not in session or session['email'] != 'jamalassaki@hotmail.fr':
        return redirect(url_for('login'))
    if request.method == 'POST':
        email = request.form['email']
        date_debut = request.form['date_debut']
        date_fin = request.form['date_fin']
        abonnements = load_abonnements()
        abonnements.append({
            'email': email,
            'date_debut': date_debut,
            'date_fin': date_fin
        })
        with open(ABONNEMENTS_FILE, 'w') as f:
            json.dump(abonnements, f, indent=4)
        return redirect(url_for('vip'))
    return render_template("add_abonne.html")

@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)
