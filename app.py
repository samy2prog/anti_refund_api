import os
import psycopg2
from flask import Flask, request, jsonify, render_template
from datetime import datetime

app = Flask(__name__)

# ✅ Connexion PostgreSQL (Remplace par ton URL correcte)
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

# ✅ Route : Tableau de bord des fraudes
@app.route("/dashboard")
def dashboard():
    db = get_db()
    if db:
        cursor = db.cursor()
        cursor.execute("""
            SELECT id, ip, user_agent, refund_count, 
                   CAST(risk_score AS INTEGER) AS risk_score, 
                   TO_CHAR(created_at, 'DD-MM-YYYY HH24:MI:SS') AS created_at
            FROM users
            ORDER BY created_at DESC
        """)
        users = cursor.fetchall()
        cursor.close()
        db.close()

        print("📊 Données chargées dans le dashboard:", users)  # Debug
        return render_template("dashboard.html", users=users)
    else:
        return "❌ Impossible de se connecter à la base de données.", 500

# ✅ Enregistrement d'un achat
@app.route("/buy", methods=["POST"])
def buy():
    try:
        data = request.json
        print("📥 Achat reçu:", data)  # ✅ Debug

        product_name = data.get("product_name")
        payment_method = data.get("payment_method")
        user_ip = request.remote_addr
        user_agent = request.headers.get("User-Agent")
        created_at = datetime.utcnow()  # ✅ Format correct

        db = get_db()
        if db:
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO orders (product_name, ip, user_agent, payment_method, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (product_name, user_ip, user_agent, payment_method, created_at))

            db.commit()
            cursor.close()
            db.close()

        return jsonify({"message": "Achat enregistré"})

    except Exception as e:
        print("❌ Erreur API achat:", e)
        return jsonify({"error": str(e)}), 500

# ✅ Vérification connexion PostgreSQL
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
