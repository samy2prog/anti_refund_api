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

# ✅ Correction du dashboard avec `risk_score` bien en int
@app.route("/dashboard")
def dashboard():
    db = get_db()
    if db:
        cursor = db.cursor()
        cursor.execute("""
            SELECT id, ip, user_agent, refund_count, 
                   CAST(risk_score AS INTEGER) AS risk_score, 
                   created_at
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

