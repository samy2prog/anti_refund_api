import os
import psycopg2
import requests
from flask import Flask, request, jsonify, render_template
from datetime import datetime

app = Flask(__name__)

# ✅ Connexion à PostgreSQL
DATABASE_URL = "postgresql://eshop_db_d9qc_user:6IoPk0zWxCmDL9EEQshbWrmK54bdfced@dpg-cv93lh1u0jms73eevl00-a.frankfurt-postgres.render.com/eshop_db_d9qc"
IPINFO_TOKEN = "93b78ea229f200"  # 🔹 Remplace par ton vrai token ipinfo.io

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

# ✅ Analyse l'IP avec ipinfo.io
def analyze_ip(ip):
    try:
        response = requests.get(f"https://ipinfo.io/{ip}?token={IPINFO_TOKEN}")
        data = response.json()
        return {
            "country": data.get("country", "Unknown"),
            "city": data.get("city", "Unknown"),
            "isp": data.get("org", "Unknown"),
            "is_proxy": "proxy" in data.get("privacy", {})
        }
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse IP : {e}")
        return None

# ✅ Calcul du score de risque amélioré
def calculate_risk_score(refund_count, payment_method, ip_info):
    risk_score = refund_count * 20  # 🔹 Augmente le risque pour chaque remboursement

    if payment_method == "crypto":
        risk_score += 30  # 🔹 Les paiements anonymes sont plus risqués

    if ip_info["is_proxy"]:
        risk_score += 40  # 🔹 Les proxys et VPN sont souvent utilisés pour la fraude

    if ip_info["country"] not in ["FR", "DE", "US"]:  # 🔹 Pays moins sûrs
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

        ip_info = analyze_ip(user_ip)  # 🔍 Analyse de l'IP

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

            # ✅ Calcul du risque
            risk_score = calculate_risk_score(refund_count, payment_method, ip_info)

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

        return jsonify({"message": "Achat enregistré", "risk_score": risk_score, "ip_info": ip_info})

    except Exception as e:
        print("❌ Erreur API achat:", e)
        return jsonify({"error": str(e)}), 500

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
