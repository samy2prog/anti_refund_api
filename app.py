import os
import psycopg2
from flask import Flask, request, jsonify, render_template
from datetime import datetime

app = Flask(__name__)

# ✅ Connexion à PostgreSQL (EXTERNAL DATABASE URL pour Render)
DATABASE_URL = "postgresql://eshop_db_d9qc_user:6IoPk0zWxCmDL9EEQshbWrmK54bdfced@dpg-cv93lh1u0jms73eevl00-a.frankfurt-postgres.render.com/eshop_db_d9qc"

def get_db():
    """Connexion à PostgreSQL"""
    try:
        print("🔗 Connexion à PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        print("✅ Connexion réussie !")
        return conn
    except psycopg2.OperationalError as e:
        print("❌ ERREUR DE CONNEXION À POSTGRESQL :", e)
        return None

# ✅ Algorithme avancé de calcul du risque
def calculate_risk_score(refund_count, payment_method, ip, recent_purchases):
    risk_score = 0

    if refund_count >= 2:
        risk_score += 40

    if payment_method == "crypto":
        risk_score += 30

    risky_ips = ["123.45.67.89", "98.76.54.32"]  # Exemple d'IP suspectes
    if ip in risky_ips:
        risk_score += 25

    if recent_purchases >= 3:
        risk_score += 15

    return min(risk_score, 100)

# ✅ Enregistrer un achat et mettre à jour `users`
@app.route("/buy", methods=["POST"])
def buy():
    try:
        data = request.json
        print("📥 Achat reçu:", data)  # ✅ Debug

        product_name = data.get("product_name")
        payment_method = data.get("payment_method")
        user_ip = request.remote_addr
        user_agent = request.headers.get("User-Agent")
        created_at = datetime.utcnow()

        db = get_db()
        if db:
            cursor = db.cursor()

            # ✅ Insérer l'achat dans `orders`
            cursor.execute("""
                INSERT INTO orders (product_name, ip, user_agent, payment_method, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (product_name, user_ip, user_agent, payment_method, created_at))

            # ✅ Vérifier si l'utilisateur existe déjà
            cursor.execute("SELECT refund_count FROM users WHERE ip = %s", (user_ip,))
            result = cursor.fetchone()
            refund_count = result[0] if result else 0

            # ✅ Vérifier les achats récents
            cursor.execute("SELECT COUNT(*) FROM orders WHERE ip = %s AND created_at > NOW() - INTERVAL '1 hour'", (user_ip,))
            recent_purchases = cursor.fetchone()[0]

            # ✅ Calcul du risque
            risk_score = calculate_risk_score(refund_count, payment_method, user_ip, recent_purchases)

            # ✅ Insérer ou mettre à jour `users`
            cursor.execute("""
                INSERT INTO users (ip, user_agent, refund_count, risk_score, created_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (ip) DO UPDATE
                SET refund_count = users.refund_count, risk_score = EXCLUDED.risk_score, created_at = EXCLUDED.created_at
            """, (user_ip, user_agent, refund_count, risk_score, created_at))

            db.commit()
            cursor.close()
            db.close()

            print(f"✅ Utilisateur {user_ip} ajouté ou mis à jour avec risk_score = {risk_score}")

        return jsonify({"message": "Achat enregistré", "risk_score": risk_score})

    except Exception as e:
        print("❌ Erreur API achat:", e)
        return jsonify({"error": str(e)}), 500

# ✅ Enregistrer une demande de remboursement
@app.route("/refund/<int:order_id>")
def request_refund(order_id):
    try:
        db = get_db()
        if db:
            cursor = db.cursor()

            # ✅ Marquer la commande comme remboursée
            cursor.execute("UPDATE orders SET refund_requested = TRUE WHERE id = %s", (order_id,))
            cursor.execute("SELECT ip FROM orders WHERE id = %s", (order_id,))
            user_ip = cursor.fetchone()[0]

            # ✅ Mettre à jour le compte utilisateur
            cursor.execute("SELECT refund_count FROM users WHERE ip = %s", (user_ip,))
            result = cursor.fetchone()
            refund_count = result[0] + 1 if result else 1
            risk_score = refund_count * 20  # Augmentation du risque après remboursement

            cursor.execute("UPDATE users SET refund_count = %s, risk_score = %s WHERE ip = %s", (refund_count, risk_score, user_ip))

            db.commit()
            cursor.close()
            db.close()

        return jsonify({"message": "Remboursement enregistré", "risk_score": risk_score})

    except Exception as e:
        print("❌ Erreur API remboursement:", e)
        return jsonify({"error": str(e)}), 500

# ✅ Affichage du Dashboard
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

        return render_template("dashboard.html", users=users)
    else:
        return "❌ Impossible de se connecter à la base de données."

# ✅ Tester la connexion à la base de données
@app.route("/test-db")
def test_db():
    try:
        db = get_db()
        if db:
            cursor = db.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            db.close()
            return "✅ Connexion à PostgreSQL réussie !"
        else:
            return "❌ Impossible de se connecter à PostgreSQL"
    except Exception as e:
        return f"❌ Erreur PostgreSQL : {e}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
