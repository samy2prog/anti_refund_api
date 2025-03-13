import os
import psycopg2
from flask import Flask, request, jsonify, render_template
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

# ✅ Algorithme avancé de calcul du risque
def calculate_risk_score(refund_count, payment_method, ip, recent_purchases, multiple_accounts):
    risk_score = 0

    if refund_count >= 2:
        risk_score += 40

    if payment_method == "crypto":
        risk_score += 30

    risky_ips = ["123.45.67.89", "98.76.54.32"]
    if ip in risky_ips:
        risk_score += 25

    if multiple_accounts:
        risk_score += 20

    if recent_purchases >= 3:
        risk_score += 15

    return min(risk_score, 100)

# ✅ Enregistrer un achat et le lier au dashboard
@app.route("/buy", methods=["POST"])
def buy():
    data = request.json
    product_name = data.get("product_name")
    payment_method = data.get("payment_method")
    user_ip = request.remote_addr
    user_agent = request.headers.get("User-Agent")
    created_at = datetime.utcnow()

    db = get_db()
    if db:
        cursor = db.cursor()

        # ✅ Enregistrer l'achat dans `orders`
        cursor.execute("""
            INSERT INTO orders (product_name, ip, user_agent, payment_method, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (product_name, user_ip, user_agent, payment_method, created_at))

        # ✅ Vérifier l’historique de l'utilisateur
        cursor.execute("SELECT COUNT(*) FROM orders WHERE ip = %s AND created_at > NOW() - INTERVAL '1 hour'", (user_ip,))
        recent_purchases = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT ip) FROM users WHERE ip = %s", (user_ip,))
        multiple_accounts = cursor.fetchone()[0] > 1

        # ✅ Récupérer le `refund_count`
        cursor.execute("SELECT refund_count FROM users WHERE ip = %s", (user_ip,))
        refund_data = cursor.fetchone()
        refund_count = refund_data[0] if refund_data else 0

        # ✅ Calcul du risque
        risk_score = calculate_risk_score(refund_count, payment_method, user_ip, recent_purchases, multiple_accounts)

        # ✅ Enregistrer dans `users`
        cursor.execute("""
            INSERT INTO users (ip, user_agent, refund_count, risk_score, created_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (ip) DO UPDATE
            SET refund_count = users.refund_count, risk_score = %s, created_at = %s
        """, (user_ip, user_agent, refund_count, risk_score, created_at, risk_score, created_at))

        db.commit()
        cursor.close()
        db.close()

    return jsonify({"message": "Achat enregistré", "risk_score": risk_score})

# ✅ Enregistrer une demande de remboursement
@app.route("/refund/<int:order_id>")
def request_refund(order_id):
    db = get_db()
    if db:
        cursor = db.cursor()

        cursor.execute("UPDATE orders SET refund_requested = TRUE WHERE id = %s", (order_id,))
        cursor.execute("SELECT ip FROM orders WHERE id = %s", (order_id,))
        user_ip = cursor.fetchone()[0]

        cursor.execute("SELECT refund_count FROM users WHERE ip = %s", (user_ip,))
        refund_count = cursor.fetchone()[0] + 1
        risk_score = refund_count * 20

        cursor.execute("UPDATE users SET refund_count = %s, risk_score = %s WHERE ip = %s", (refund_count, risk_score, user_ip))

        db.commit()
        cursor.close()
        db.close()

    return jsonify({"message": "Remboursement enregistré", "risk_score": risk_score})

# ✅ Affichage du Dashboard
@app.route("/dashboard")
def dashboard():
    db = get_db()
    if db:
        cursor = db.cursor()
        cursor.execute("""
            SELECT u.id, u.ip, u.user_agent, u.refund_count, u.risk_score, u.created_at, 
                   COALESCE(o.product_name, 'N/A') AS product_name, COALESCE(o.refund_requested, FALSE) AS refund_requested
            FROM users u
            LEFT JOIN orders o ON u.ip = o.ip
            ORDER BY u.created_at DESC
        """)
        users = cursor.fetchall()
        cursor.close()
        db.close()

        return render_template("dashboard.html", users=users)
    else:
        return "❌ Impossible de se connecter à la base de données."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
