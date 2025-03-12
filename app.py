import psycopg2
import hashlib
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# ✅ Connexion PostgreSQL avec Render (Utilise l'Internal Database URL)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://eshop_user:Idx7b2u8UfXodOCQn3oGHwrzwtyP3CbI@dpg-cv908nin91rc73d5bes0-a/eshop_db_c764")

def get_db():
    """Connexion à PostgreSQL"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.OperationalError as e:
        print("❌ ERREUR DE CONNEXION À POSTGRESQL :", e)
        return None

# ✅ Création des tables si elles n'existent pas
def create_tables():
    db = get_db()
    if db:
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                ip TEXT NOT NULL,
                user_agent TEXT NOT NULL,
                fingerprint TEXT UNIQUE NOT NULL,
                refund_count INTEGER DEFAULT 0,
                risk_score INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
        cursor.close()
        db.close()
        print("✅ Tables créées avec succès.")

# ✅ Générer une empreinte utilisateur unique
def generate_fingerprint(user_agent, ip):
    return hashlib.sha256(f"{user_agent}{ip}".encode()).hexdigest()

# ✅ Calcul du score de risque
def calculate_risk_score(ip_info, refund_count, payment_method):
    risk_score = refund_count * 10
    if payment_method == "crypto":
        risk_score += 20
    return min(risk_score, 100)  # Le score est plafonné à 100

# ✅ Route pour détecter la fraude
@app.route("/detect", methods=["POST"])
def detect_fraud():
    data = request.json
    ip = data.get("ip")
    user_agent = data.get("user_agent")
    payment_method = data.get("payment_method")
    refund_count = data.get("refund_count", 0)

    fingerprint = generate_fingerprint(user_agent, ip)
    risk_score = calculate_risk_score(ip, refund_count, payment_method)

    db = get_db()
    if db:
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO users (ip, user_agent, fingerprint, refund_count, risk_score)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (fingerprint) DO UPDATE
            SET refund_count = users.refund_count + 1, risk_score = EXCLUDED.risk_score
        """, (ip, user_agent, fingerprint, refund_count, risk_score))
        db.commit()
        cursor.close()
        db.close()

    return jsonify({
        "fingerprint": fingerprint,
        "risk_score": risk_score
    })

# ✅ Route du tableau de bord des fraudes
@app.route("/dashboard")
def dashboard():
    db = get_db()
    if db:
        cursor = db.cursor()
        cursor.execute("SELECT id, ip, user_agent, fingerprint, refund_count, risk_score, created_at FROM users ORDER BY risk_score DESC")
        users = cursor.fetchall()
        cursor.close()
        db.close()

        html = "<h1>Tableau de Bord - Détection des Fraudes</h1>"
        html += "<table border='1'><tr><th>ID</th><th>IP</th><th>User Agent</th><th>Empreinte</th><th>Remboursements</th><th>Risk Score</th><th>Date</th></tr>"
        for user in users:
            row_color = "red" if user[5] >= 50 else "white"
            html += f"<tr style='background-color:{row_color}'><td>{user[0]}</td><td>{user[1]}</td><td>{user[2]}</td><td>{user[3][:10]}...</td><td>{user[4]}</td><td>{user[5]}</td><td>{user[6]}</td></tr>"
        html += "</table>"
        return html
    else:
        return "❌ Impossible de se connecter à la base de données."

# ✅ Lancer l’application
if __name__ == "__main__":
    create_tables()
    app.run(host="0.0.0.0", port=5000, debug=True)
