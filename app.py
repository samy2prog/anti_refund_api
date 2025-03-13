import os
import psycopg2
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# ✅ Connexion PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://eshop_user:Idx7b2u8UfXodOCQn3oGHwrzwtyP3CbI@dpg-cv908nin91rc73d5bes0-a/eshop_db_c764")

def get_db():
    """Connexion à PostgreSQL"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.OperationalError as e:
        print("❌ ERREUR DE CONNEXION À POSTGRESQL :", e)
        return None

# ✅ Algorithme amélioré de calcul du score de risque
def calculate_risk_score(refund_count, payment_method, ip, user_history):
    risk_score = 0

    # 🔴 Trop de remboursements récents
    if refund_count >= 2:
        risk_score += 30

    # 🔴 Paiement en crypto = risque élevé
    if payment_method == "crypto":
        risk_score += 20

    # 🔴 Vérifier si l'IP est associée à un VPN/proxy/datacenter
    risky_ips = ["123.45.67.89", "98.76.54.32"]  # Exemples d’IP suspectes
    if ip in risky_ips:
        risk_score += 25

    # 🔴 Vérifier si cette IP est liée à plusieurs comptes
    if len(set(user_history)) > 1:
        risk_score += 15

    # 🔴 Achat massif en peu de temps
    if len(user_history) >= 5:
        risk_score += 10

    return min(risk_score, 100)  # 🔥 On s’assure que le score ne dépasse pas 100

# ✅ Route pour détecter la fraude
@app.route("/detect", methods=["POST"])
def detect_fraud():
    data = request.json
    ip = data.get("ip")
    user_agent = data.get("user_agent")
    payment_method = data.get("payment_method")
    refund_count = data.get("refund_count", 0)
    created_at = datetime.utcnow()

    db = get_db()
    if db:
        cursor = db.cursor()

        # 🔎 Vérifier l'historique d'achat de cet utilisateur
        cursor.execute("SELECT product_name FROM orders WHERE ip = %s", (ip,))
        user_history = cursor.fetchall()

        # 🛑 Calculer le risque avec l'algorithme amélioré
        risk_score = calculate_risk_score(refund_count, payment_method, ip, user_history)

        # 🔐 Enregistrer dans la base de données
        cursor.execute("""
            INSERT INTO users (ip, user_agent, refund_count, risk_score, created_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (ip) DO UPDATE
            SET refund_count = users.refund_count + 1, risk_score = EXCLUDED.risk_score, created_at = EXCLUDED.created_at
        """, (ip, user_agent, refund_count, risk_score, created_at))

        db.commit()
        cursor.close()
        db.close()

    return jsonify({
        "risk_score": risk_score,
        "ip": ip,
        "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    })

# ✅ Route pour afficher le Dashboard trié par date
@app.route("/dashboard")
def dashboard():
    db = get_db()
    if db:
        cursor = db.cursor()
        cursor.execute("""
            SELECT u.id, u.ip, u.user_agent, u.refund_count, u.risk_score, u.created_at
            FROM users u
            ORDER BY u.created_at DESC
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
                .low-risk { background-color: #c8e6c9; color: #2e7d32; font-weight: bold; }
                .medium-risk { background-color: #ffcc80; color: #e65100; font-weight: bold; }
                .high-risk { background-color: #ef9a9a; color: #b71c1c; font-weight: bold; }
            </style>
        </head>
        <body>
            <h1>🚀 Tableau de Bord - Détection des Fraudes</h1>
            <table>
                <tr>
                    <th>ID</th><th>IP</th><th>User Agent</th>
                    <th>Remboursements</th><th>Risk Score</th><th>Date</th>
                </tr>
        """

        for user in users:
            row_class = "low-risk" if user[4] < 30 else "medium-risk" if user[4] < 70 else "high-risk"
            formatted_date = user[5].strftime("%Y-%m-%d %H:%M:%S UTC") if user[5] else "N/A"

            html += f"""
            <tr class='{row_class}'>
                <td>{user[0]}</td>
                <td>{user[1]}</td>
                <td>{user[2][:30]}...</td>
                <td>{user[3]}</td>
                <td>{user[4]}</td>
                <td>{formatted_date}</td>
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
