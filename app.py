import os
import psycopg2
import hashlib
from flask import Flask, request, jsonify

app = Flask(__name__)

# ✅ Connexion PostgreSQL (Render Internal Database URL)
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
            );
            
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                product_name TEXT NOT NULL,
                ip TEXT NOT NULL,
                user_agent TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                refund_requested BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        db.commit()
        cursor.close()
        db.close()
        print("✅ Tables créées avec succès.")

# ✅ Générer une empreinte utilisateur unique
def generate_fingerprint(user_agent, ip):
    return hashlib.sha256(f"{user_agent}{ip}".encode()).hexdigest()

# ✅ Calcul du score de risque
def calculate_risk_score(refund_count, payment_method):
    risk_score = refund_count * 10
    if payment_method == "crypto":
        risk_score += 20
    return min(risk_score, 100)  # Score max = 100

# ✅ Route pour la page d'accueil
@app.route("/")
def home():
    return "🚀 API de Détection de Fraude en ligne ! Utilisez `/detect` et `/dashboard`."

# ✅ Route pour détecter la fraude
@app.route("/detect", methods=["POST"])
def detect_fraud():
    data = request.json
    ip = data.get("ip")
    user_agent = data.get("user_agent")
    payment_method = data.get("payment_method")
    refund_count = data.get("refund_count", 0)

    fingerprint = generate_fingerprint(user_agent, ip)
    risk_score = calculate_risk_score(refund_count, payment_method)

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
        cursor.execute("""
            SELECT u.id, u.ip, u.user_agent, u.fingerprint, u.refund_count, u.risk_score, u.created_at, 
                   COALESCE(o.product_name, 'N/A') AS product_name, COALESCE(o.refund_requested, FALSE) AS refund_requested
            FROM users u
            LEFT JOIN orders o ON u.ip = o.ip
            ORDER BY u.risk_score DESC
        """)
        users = cursor.fetchall()
        cursor.close()
        db.close()

        html = """
        <html>
        <head>
            <title>Tableau de Bord - Détection des Fraudes</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; background-color: #f4f4f4; }
                h1 { color: #333; }
                table { width: 90%; margin: auto; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2); }
                th, td { padding: 12px; border: 1px solid #ddd; text-align: center; }
                th { background-color: #222; color: white; }
                .low-risk { background-color: #c8e6c9; color: #2e7d32; font-weight: bold; }  /* 🟢 Vert */
                .medium-risk { background-color: #ffcc80; color: #e65100; font-weight: bold; } /* 🟠 Orange */
                .high-risk { background-color: #ef9a9a; color: #b71c1c; font-weight: bold; } /* 🔴 Rouge */
                .refund { background-color: #fdd835; color: #bf360c; font-weight: bold; } /* 🟡 Jaune remboursement */
            </style>
        </head>
        <body>
            <h1>🚀 Tableau de Bord - Détection des Fraudes</h1>
            <table>
                <tr>
                    <th>ID</th><th>IP</th><th>User Agent</th><th>Empreinte</th>
                    <th>Remboursements</th><th>Risk Score</th><th>Date</th><th>Produit</th><th>Remboursement</th>
                </tr>
        """

        for user in users:
            if user[5] < 30:
                row_class = "low-risk"  # 🟢 Faible risque
            elif user[5] < 70:
                row_class = "medium-risk"  # 🟠 Risque moyen
            else:
                row_class = "high-risk"  # 🔴 Risque élevé

            refund_status = "✅ Oui" if user[8] else "❌ Non"
            if user[8]:  # 🟡 Remboursement demandé
                row_class = "refund"

            html += f"""
            <tr class='{row_class}'>
                <td>{user[0]}</td>
                <td>{user[1]}</td>
                <td>{user[2][:30]}...</td>
                <td>{user[3][:10]}...</td>
                <td>{user[4]}</td>
                <td>{user[5]}</td>
                <td>{user[6]}</td>
                <td>{user[7]}</td>
                <td>{refund_status}</td>
            </tr>
            """

        html += """
            </table>
        </body>
        </html>
        """
        return html
    else:
        return "❌ Impossible de se connecter à la base de données."

# ✅ Lancer l’application avec le port Render
if __name__ == "__main__":
    create_tables()
    port = int(os.environ.get("PORT", 10000))  # Utilise le port attribué par Render
    app.run(host="0.0.0.0", port=port, debug=True)
