from flask import Flask, request, jsonify, render_template, send_from_directory
import psycopg2
from datetime import datetime
import os

app = Flask(__name__, static_folder="static")

# ✅ Connexion à la base de données
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://eshop_db_d9qc_user:6IoPk0zWxCmDL9EEQshbWrmK54bdfced@dpg-cv93lh1u0jms73eevl00-a.frankfurt-postgres.render.com/eshop_db_d9qc")

def connect_db():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"❌ ERREUR CONNEXION DB : {e}")
        return None

# ✅ Servir les fichiers statiques (CSS, JS)
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

# ✅ Route Achat (BUY)
@app.route("/buy", methods=["POST"])
def buy():
    data = request.get_json()
    product_name = data.get("product_name")
    payment_method = data.get("payment_method")

    if not product_name or not payment_method:
        return jsonify({"error": "Données incomplètes"}), 400

    ip_address = request.remote_addr  # ✅ Récupération IP
    user_agent = request.headers.get("User-Agent", "Inconnu")

    print(f"📡 IP récupérée : {ip_address} | User-Agent : {user_agent}")  # Debug

    conn = connect_db()
    if not conn:
        return jsonify({"error": "Connexion DB impossible"}), 500
    
    cur = conn.cursor()

    try:
        # ✅ Enregistrement de la commande
        cur.execute(
            "INSERT INTO orders (product_name, ip, user_agent, payment_method, created_at) VALUES (%s, %s, %s, %s, NOW()) RETURNING id",
            (product_name, ip_address, user_agent, payment_method)
        )
        order_id = cur.fetchone()[0]
        conn.commit()

        # ✅ Vérification utilisateur
        cur.execute("SELECT id FROM users WHERE ip = %s", (ip_address,))
        user = cur.fetchone()

        if not user:
            # ✅ Création utilisateur si inexistant
            cur.execute(
                "INSERT INTO users (ip, user_agent, fingerprint, refund_count, risk_score, created_at) VALUES (%s, %s, %s, %s, %s, NOW())",
                (ip_address, user_agent, "default_fingerprint", 0, 10)  # Risk Score 10 par défaut
            )
            conn.commit()

        cur.close()
        conn.close()

        return jsonify({"message": "Commande enregistrée avec succès", "order_id": order_id}), 201

    except Exception as e:
        conn.rollback()
        print(f"❌ ERREUR INSERTION : {e}")
        return jsonify({"error": str(e)}), 500

# ✅ Route Remboursement (REFUND)
@app.route("/refund", methods=["POST"])
def refund():
    data = request.get_json()
    order_id = data.get("order_id")

    if not order_id:
        return jsonify({"error": "ID de commande manquant"}), 400

    conn = connect_db()
    if not conn:
        return jsonify({"error": "Connexion DB impossible"}), 500
    
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO refunds (order_id, status, created_at) VALUES (%s, 'En attente', NOW())",
            (order_id,)
        )
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"message": "Remboursement demandé avec succès"}), 201

    except Exception as e:
        conn.rollback()
        print(f"❌ ERREUR REMBOURSEMENT : {e}")
        return jsonify({"error": str(e)}), 500

# ✅ Route du Dashboard
@app.route("/dashboard")
def dashboard():
    conn = connect_db()
    if not conn:
        return "Erreur de connexion à la base de données", 500

    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("dashboard.html", users=users)

# ✅ Lancement avec gestion dynamique des ports pour éviter les erreurs 502
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # 🌍 Render et local support
    app.run(host="0.0.0.0", port=port, debug=True)
