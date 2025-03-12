from flask import Flask, request, jsonify, render_template
import psycopg2
import hashlib
import os

app = Flask(__name__)

# 🔹 Configuration PostgreSQL sur Render
DATABASE_URL = "postgresql://eshop_user:Idx7b2u8UfXodOCQn3oGHwrzwtyP3CbI@dpg-cv908nin91rc73d5bes0-a.internal/render.com/eshop_db_c764"

def get_db():
    """Connexion à la base PostgreSQL"""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# 🔹 Création des tables dans PostgreSQL
def create_tables():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            ip TEXT,
            user_agent TEXT,
            fingerprint TEXT UNIQUE,
            refund_count INTEGER DEFAULT 0,
            risk_score INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()
    cursor.close()
    db.close()

create_tables()

def generate_fingerprint(user_agent, ip):
    """Génère une empreinte unique de l'utilisateur"""
    fingerprint = hashlib.sha256(f"{user_agent}{ip}".encode()).hexdigest()
    return fingerprint

def calculate_risk_score(refund_count, payment_method):
    """Calcule un score de risque basé sur le nombre de remboursements et la méthode de paiement"""
    risk_score = refund_count * 10  # Chaque remboursement ajoute 10 points de risque
    if payment_method == "crypto":
        risk_score += 20  # Paiements en crypto sont plus risqués
    return min(risk_score, 100)  # Score max = 100

@app.route("/detect", methods=["POST"])
def detect_fraud():
    """Détecte si une commande est frauduleuse"""
    data = request.json
    ip = data["ip"]
    user_agent = data["user_agent"]
    payment_method = data["payment_method"]
    refund_count = data["refund_count"]

    fingerprint = generate_fingerprint(user_agent, ip)

    db = get_db()
    cursor = db.cursor()
    
    # Vérifier si l'utilisateur existe déjà
    cursor.execute("SELECT refund_count FROM users WHERE fingerprint = %s", (fingerprint,))
    user = cursor.fetchone()

    if user:
        refund_count += user[0]  # Ajoute les remboursements existants

    risk_score = calculate_risk_score(refund_count, payment_method)

    if user:
        cursor.execute("UPDATE users SET refund_count = %s, risk_score = %s WHERE fingerprint = %s",
                       (refund_count, risk_score, fingerprint))
    else:
        cursor.execute("""
            INSERT INTO users (ip, user_agent, fingerprint, refund_count, risk_score)
            VALUES (%s, %s, %s, %s, %s)
        """, (ip, user_agent, fingerprint, refund_count, risk_score))

    db.commit()
    cursor.close()
    db.close()

    return jsonify({
        "fingerprint": fingerprint,
        "risk_score": risk_score
    })

@app.route("/dashboard")
def dashboard():
    """Affiche le tableau de bord avec la liste des fraudes enregistrées"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, ip, user_agent, fingerprint, refund_count, risk_score, created_at FROM users ORDER BY risk_score DESC")
    users = cursor.fetchall()
    cursor.close()
    db.close()
    
    return render_template("dashboard.html", users=users)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
