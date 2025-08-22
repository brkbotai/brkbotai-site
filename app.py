from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, date
import json
import os
import csv
from werkzeug.security import generate_password_hash, check_password_hash

# ──────────────────────────────────────────────────────────────────────────────
# Config Flask
# ──────────────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'change-me')

# Chemins "locaux" (dans l'image)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ABONNEMENTS_JSON_LOCAL = os.path.join(BASE_DIR, 'abonnements.json')
ABONNEMENTS_CSV_LOCAL  = os.path.join(BASE_DIR, 'abonnements.csv')
USERS_FILE_LOCAL       = os.path.join(BASE_DIR, 'users.json')
PRONOS_FILE_LOCAL      = os.path.join(BASE_DIR, 'pronos.json')

# Chemins "persistants" (Render Disk via env) — prioritaire si présent
ABONNEMENTS_PATH = os.getenv('ABONNEMENTS_PATH', '/data/abonnements.json')
USERS_PATH       = os.getenv('USERS_PATH', '/data/users.json')
PRONOS_PATH      = os.getenv('PRONOS_PATH', '/data/pronos.json')

ADMIN_EMAILS = {e.strip().lower() for e in os.getenv('ADMIN_EMAILS', 'jamalassaki@hotmail.fr').split(',')}
SUB_CHECK_DISABLED = os.getenv('SUB_CHECK_DISABLED', '0').lower() in {'1', 'true', 'yes'}

# ──────────────────────────────────────────────────────────────────────────────
# Helpers FS / JSON
# ──────────────────────────────────────────────────────────────────────────────
def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)

def _read_json(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def _write_json(path: str, data):
    _ensure_dir(path)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def _bootstrap_from_local_if_missing(persistent_path: str, local_path: str, default_data):
    """
    Si le fichier persistant (/data/...) n'existe pas, mais qu'un fichier local existe,
    on le copie une seule fois. Sinon, on écrit default_data si rien n'existe.
    """
    if os.path.exists(persistent_path):
        return
    if os.path.exists(local_path):
        try:
            data = _read_json(local_path)
        except Exception:
            data = default_data
        _write_json(persistent_path, data)
    else:
        _write_json(persistent_path, default_data)

# Bootstrap au démarrage pour garantir les fichiers sur le Disk
_bootstrap_from_local_if_missing(ABONNEMENTS_PATH, ABONNEMENTS_JSON_LOCAL, [])
_bootstrap_from_local_if_missing(USERS_PATH,       USERS_FILE_LOCAL,       [])
_bootstrap_from_local_if_missing(PRONOS_PATH,      PRONOS_FILE_LOCAL,      {"pronos": []})

# ──────────────────────────────────────────────────────────────────────────────
# Abonnements
# ──────────────────────────────────────────────────────────────────────────────
def load_abonnements():
    """Charge les abonnements depuis le chemin persistant, fallback CSV local si vide."""
    subs = {}
    # Chemin persistant prioritaire
    if os.path.exists(ABONNEMENTS_PATH):
        try:
            data = _read_json(ABONNEMENTS_PATH) or []
            for r in data:
                email = (r.get('email') or '').strip().lower()
                if email:
                    subs[email] = {
                        'email': email,
                        'date_debut': r.get('date_debut', ''),
                        'date_fin': r.get('date_fin', '')
                    }
            if subs:
                return subs
        except Exception as e:
            app.logger.error(f"[ABO] Erreur lecture {ABONNEMENTS_PATH}: {e}")

    # Fallback JSON local (si jamais)
    if os.path.exists(ABONNEMENTS_JSON_LOCAL):
        try:
            data = _read_json(ABONNEMENTS_JSON_LOCAL) or []
            for r in data:
                email = (r.get('email') or '').strip().lower()
                if email:
                    subs[email] = {
                        'email': email,
                        'date_debut': r.get('date_debut', ''),
                        'date_fin': r.get('date_fin', '')
                    }
            if subs:
                return subs
        except Exception as e:
            app.logger.error(f"[ABO] Erreur lecture {ABONNEMENTS_JSON_LOCAL}: {e}")

    # Fallback CSV local (vieux format)
    if os.path.exists(ABONNEMENTS_CSV_LOCAL):
        try:
            with open(ABONNEMENTS_CSV_LOCAL, newline='', encoding='utf-8') as f:
                for r in csv.DictReader(f):
                    email = (r.get('email') or '').strip().lower()
                    if email:
                        subs[email] = {
                            'email': email,
                            'date_debut': r.get('date_debut', ''),
                            'date_fin': r.get('date_fin', '')
                        }
        except Exception as e:
            app.logger.error(f"[ABO] Erreur lecture CSV {ABONNEMENTS_CSV_LOCAL}: {e}")

    return subs

def save_abonnements(subs_dict):
    data = list(subs_dict.values())
    _write_json(ABONNEMENTS_PATH, data)

SUBS = load_abonnements()

def is_admin(email: str) -> bool:
    return bool(email) and email.strip().lower() in ADMIN_EMAILS

def is_subscription_valid(email: str) -> bool:
    """True si: bypass ON, admin, ou date_fin >= today (inclusive)."""
    if not email:
        return False
    email_n = email.strip().lower()
    if SUB_CHECK_DISABLED or is_admin(email_n):
        return True
    rec = SUBS.get(email_n)
    if not rec:
        return False
    try:
        end = datetime.strptime(rec['date_fin'], '%Y-%m-%d').date()
    except Exception:
        return False
    return date.today() <= end

# ──────────────────────────────────────────────────────────────────────────────
# Users
# ──────────────────────────────────────────────────────────────────────────────
def load_users():
    try:
        return _read_json(USERS_PATH) or []
    except Exception as e:
        app.logger.error(f"[USERS] Erreur lecture {USERS_PATH}: {e}")
        # Fallback local en lecture seule
        try:
            return _read_json(USERS_FILE_LOCAL) or []
        except Exception:
            return []

def save_users(users):
    _write_json(USERS_PATH, users)

# ──────────────────────────────────────────────────────────────────────────────
# Pronos
# ──────────────────────────────────────────────────────────────────────────────
def load_pronos():
    try:
        obj = _read_json(PRONOS_PATH) or {"pronos": []}
        return obj.get('pronos', [])
    except Exception as e:
        app.logger.error(f"[PRONOS] Erreur lecture {PRONOS_PATH}: {e}")
        # Fallback local
        try:
            obj = _read_json(PRONOS_FILE_LOCAL) or {"pronos": []}
            return obj.get('pronos', [])
        except Exception:
            return []

def save_pronos(pronos_list):
    _write_json(PRONOS_PATH, {"pronos": pronos_list})

# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────
@app.route('/__status')
def __status():
    return {
        "bypass": SUB_CHECK_DISABLED,
        "admin_emails": list(ADMIN_EMAILS),
        "subs_count": len(SUBS),
        "paths": {
            "abonnements_path": ABONNEMENTS_PATH,
            "abonnements_path_exists": os.path.exists(ABONNEMENTS_PATH),
            "users_path": USERS_PATH,
            "users_path_exists": os.path.exists(USERS_PATH),
            "pronos_path": PRONOS_PATH,
            "pronos_path_exists": os.path.exists(PRONOS_PATH),
        },
        "locals_exist": {
            "abo_json_local": os.path.exists(ABONNEMENTS_JSON_LOCAL),
            "abo_csv_local": os.path.exists(ABONNEMENTS_CSV_LOCAL),
            "users_local": os.path.exists(USERS_FILE_LOCAL),
            "pronos_local": os.path.exists(PRONOS_FILE_LOCAL),
        }
    }

@app.route('/')
def index():
    pronos = load_pronos()
    return render_template('index.html', pronos=pronos)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        pwd = request.form['password']
        confirm = request.form['confirm']
        if pwd != confirm:
            return 'Les mots de passe ne correspondent pas'
        users = load_users()
        if any((u.get('email','').strip().lower() == email) for u in users):
            return 'Cet email est déjà utilisé'
        users.append({'email': email, 'password': generate_password_hash(pwd)})
        save_users(users)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Si déjà connecté et valide → VIP direct
    if 'email' in session and is_subscription_valid(session['email']):
        return redirect(url_for('vip'))

    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        users = load_users()
        user = next((u for u in users if (u.get('email','').strip().lower() == email)), None)
        if not user or not check_password_hash(user['password'], password):
            return 'Identifiants incorrects'
        # Autoriser l'admin même si abonnement expiré
        if not is_subscription_valid(email) and not is_admin(email):
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
    if 'email' not in session or not is_admin(session['email']):
        return redirect(url_for('login'))
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        date_debut = request.form['date_debut']
        date_fin = request.form['date_fin']
        current = load_abonnements()
        current[email] = {'email': email, 'date_debut': date_debut, 'date_fin': date_fin}
        save_abonnements(current)
        global SUBS
        SUBS = load_abonnements()
        return redirect(url_for('vip'))
    abonnements_liste = list(load_abonnements().values())
    return render_template('add_abonne.html', abonnements=abonnements_liste)

@app.route('/users')
def list_users():
    if 'email' not in session or not is_admin(session['email']):
        return redirect(url_for('login'))
    users = load_users()
    return render_template('list_users.html', users=users)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'email' not in session or not is_admin(session['email']):
        return redirect(url_for('login'))
    if request.method == 'POST':
        os.makedirs(os.path.join(BASE_DIR, 'static', 'files'), exist_ok=True)
        os.makedirs(os.path.join(BASE_DIR, 'static', 'img'), exist_ok=True)
        pdf = request.files.get('pdf')
        if pdf and pdf.filename:
            pdf.save(os.path.join(BASE_DIR, 'static', 'files', 'top5.pdf'))
        combine = request.files.get('combine')
        if combine and combine.filename:
            combine.save(os.path.join(BASE_DIR, 'static', 'img', 'combine.jpg'))
        fun = request.files.get('fun')
        if fun and fun.filename:
            fun.save(os.path.join(BASE_DIR, 'static', 'img', 'fun.jpg'))
        return "Fichiers uploadés avec succès ! <a href='/upload'>Retour</a>"
    return render_template('upload.html')

@app.route('/edit_pronos', methods=['GET','POST'])
def edit_pronos():
    if 'email' not in session or not is_admin(session['email']):
        return redirect(url_for('login'))
    if request.method == 'POST':
        pronos = []
        i = 0
        while f'match_{i}' in request.form:
            pronos.append({
                'match': request.form.get(f'match_{i}', ''),
                'prono': request.form.get(f'prono_{i}', '')
            })
            i += 1
        save_pronos(pronos)
        return redirect(url_for('index'))
    pronos = load_pronos()
    return render_template('edit_pronos.html', pronos=pronos)

@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    # En prod Render, debug=False ; ici True pour dev local
    app.run(debug=True)
