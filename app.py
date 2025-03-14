import os
import psycopg2
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# 📌 Connexion à PostgreSQL avec le bon lien
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://eshop_db_d9qc_user:6IoPk0zWxCmDL9EEQshbWrmK54bdfced@dpg-cv93lh1u0jms73eevl00-a.frankfurt-postgres.render.com/eshop_db_d9qc")

def get_db():
    """Connexion sécurisée à PostgreSQL"""
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        return conn
    except Exception as e:
        print(f"❌ ERREUR CONNEXION : {e}")
        return None

# 📌 Route principale : Affichage du Dashboard
@app.route("/dashboard")
def dashboard():
    conn = get_db()
    if conn is None:
        return jsonify({"error": "Connexion à la base de données impossible"}), 500

    cur = conn.cursor()
    cur.execute("""
        SELECT id, ip, user_agent, fingerprint, refund_count, risk_score, created_at
        FROM users ORDER BY created_at DESC
    """)
    users = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("dashboard.html", users=users)

# 📌 Ajout d'un utilisateur suspect lors d'une transaction
def insert_user(ip, user_agent, fingerprint, refund_count, risk_score):
    conn = get_db()
    if conn is None:
        return

    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (ip, user_agent, fingerprint, refund_count, risk_score, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (fingerprint) DO UPDATE
            SET refund_count = users.refund_count + 1,
                risk_score = users.risk_score + 10
            RETURNING id
        """, (ip, user_agent, fingerprint, refund_count, risk_score))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ ERREUR INSERTION UTILISATEUR : {e}")

# 📌 Route pour enregistrer un remboursement
@app.route("/refund", methods=["POST"])
def request_refund():
    if request.content_type != "application/json":
        return jsonify({"error": "Le Content-Type doit être 'application/json'"}), 415

    data = request.get_json()
    order_id = data.get("order_id")

    if not order_id:
        return jsonify({"error": "Données invalides"}), 400

    conn = get_db()
    if conn is None:
        return jsonify({"error": "Connexion à la base de données impossible"}), 500

    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO refunds (order_id, status, created_at)
            VALUES (%s, 'En attente', NOW()) RETURNING id
        """, (order_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"message": "Remboursement demandé avec succès"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 📌 Vérification de la connexion PostgreSQL
@app.route("/test-db")
def test_db():
    conn = get_db()
    if conn:
        return jsonify({"message": "Connexion PostgreSQL réussie"}), 200
    else:
        return jsonify({"error": "Connexion impossible"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

