from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# File paths
ABONNEMENTS_FILE = 'abonnements.json'
USERS_FILE = 'users.json'
PRONOS_FILE = 'pronos.json'

# Load and save functions for abonnements (JSON)
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

# Load and save functions for users (JSON)
def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

# Load pronos
def load_pronos():
    try:
        with open(PRONOS_FILE, 'r') as f:
            return json.load(f).get('pronos', [])
    except FileNotFoundError:
        return []

@app.route('/')
def index():
    pronos = load_pronos()
    return render_template('index.html', pronos=pronos)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        pwd = request.form['password']
        confirm = request.form['confirm']
        if pwd != confirm:
            return 'Les mots de passe ne correspondent pas'
        users = load_users()
        if any(u['email'] == email for u in users):
            return 'Cet email est déjà utilisé'
        users.append({'email': email, 'password': generate_password_hash(pwd)})
        save_users(users)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'email' in session and is_subscription_valid(session['email']):
        return redirect(url_for('vip'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        users = load_users()
        user = next((u for u in users if u['email'] == email), None)
        if not user or not check_password_hash(user['password'], password):
            return 'Identifiants incorrects'
        if not is_subscription_valid(email):
            return 'Abonnement non valide ou expiré'
        session['email'] = email
        return redirect(url_for('vip'))
    return render_template('login.html')

@app.route('/vip')
def vip():
    if 'email' not in session:
        return redirect(url_for('login'))
    if not is_subscription_valid(session['email']):
        return 'Abonnement expiré ou non valide.'
    return render_template('vip.html')

@app.route('/add_abonne', methods=['GET', 'POST'])
def add_abonne():
    if 'email' not in session or session['email'] != 'jamalassaki@hotmail.fr':
        return redirect(url_for('login'))
    if request.method == 'POST':
        email = request.form['email']
        date_debut = request.form['date_debut']
        date_fin = request.form['date_fin']
        abonnements = load_abonnements()
        abonnements.append({'email': email, 'date_debut': date_debut, 'date_fin': date_fin})
        with open(ABONNEMENTS_FILE, 'w') as f:
            json.dump(abonnements, f, indent=4)
        return redirect(url_for('vip'))
    abonnements = load_abonnements()
    return render_template('add_abonne.html', abonnements=abonnements)

@app.route('/users')
def list_users():
    if 'email' not in session or session['email'] != 'jamalassaki@hotmail.fr':
        return redirect(url_for('login'))
    users = load_users()
    return render_template('list_users.html', users=users)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    ADMIN_EMAIL = 'jamalassaki@hotmail.fr'
    if 'email' not in session or session['email'] != ADMIN_EMAIL:
        return redirect(url_for('login'))
    if request.method == 'POST':
        pdf = request.files.get('pdf')
        if pdf and pdf.filename:
            pdf.save(os.path.join('static/files', 'top5.pdf'))
        combine = request.files.get('combine')
        if combine and combine.filename:
            combine.save(os.path.join('static/img', 'combine.jpg'))
        fun = request.files.get('fun')
        if fun and fun.filename:
            fun.save(os.path.join('static/img', 'fun.jpg'))
        return "Fichiers uploadés avec succès ! <a href='/upload'>Retour</a>"
    return render_template('upload.html')

@app.route('/edit_pronos', methods=['GET','POST'])
def edit_pronos():
    ADMIN_EMAIL = 'jamalassaki@hotmail.fr'
    if 'email' not in session or session['email'] != ADMIN_EMAIL:
        return redirect(url_for('login'))
    if request.method == 'POST':
        data = {'pronos': []}
        i = 0
        while f'match_{i}' in request.form:
            data['pronos'].append({
                'match': request.form[f'match_{i}'],
                'prono': request.form[f'prono_{i}']
            })
            i += 1
        with open(PRONOS_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        return redirect(url_for('index'))
    pronos = load_pronos()
    return render_template('edit_pronos.html', pronos=pronos)

@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
