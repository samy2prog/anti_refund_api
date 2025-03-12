import requests
import hashlib
import psycopg2

# 🔹 Clé API pour ipinfo.io (remplace par ta propre clé)
IPINFO_TOKEN = "93b78ea229f200"

# 🔹 Connexion PostgreSQL
def connect_db():
    """Établit la connexion à la base de données PostgreSQL."""
    return psycopg2.connect(
        dbname="anti_refund_db",
        user="postgres",  # Remplace par ton utilisateur PostgreSQL
        password="ton_mot_de_passe",  # Remplace par ton mot de passe PostgreSQL
        host="localhost"
    )

# 🔹 Vérification des IPs suspectes
def check_ip(ip):
    """
    Vérifie si une IP est suspecte (VPN, proxy, Tor).
    Retourne un dictionnaire avec les informations.
    """
    try:
        url = f"https://ipinfo.io/{ip}/json?token={IPINFO_TOKEN}"
        response = requests.get(url)

        # Vérifie si la requête API a réussi
        if response.status_code != 200:
            return {"error": f"Erreur API ipinfo.io ({response.status_code}): {response.text}"}

        data = response.json()

        # Vérifier si l'IP est invalide
        if "bogon" in data:
            return {"error": "IP privée ou locale non prise en charge"}
        
        if "ip" not in data:
            return {"error": "IP non valide ou non trouvée"}

        # Extraction des informations
        org = data.get("org", "Unknown")
        country = data.get("country", "Unknown")
        region = data.get("region", "Unknown")

        # Vérifier si l'IP provient d'un VPN, proxy ou Tor
        is_suspicious = any(word in org.lower() for word in ["vpn", "proxy", "tor"])

        return {
            "ip": ip,
            "country": country,
            "region": region,
            "isp": org,
            "is_suspicious": is_suspicious
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"Erreur réseau : {str(e)}"}

# 🔹 Génération de l'empreinte digitale
def generate_fingerprint(user_agent, ip):
    """
    Génère une empreinte unique pour un utilisateur basé sur son IP et son navigateur.
    Retourne un hash SHA-256.
    """
    try:
        hash_input = f"{user_agent}{ip}"
        fingerprint = hashlib.sha256(hash_input.encode()).hexdigest()
        return fingerprint
    except Exception as e:
        return f"Erreur lors de la génération de l'empreinte: {str(e)}"

# 🔹 Vérification de l'historique de l'utilisateur
def check_user_history(fingerprint):
    """
    Vérifie si un utilisateur a déjà été détecté avec :
    - La même empreinte digitale
    - Plusieurs IPs utilisées
    Retourne un dictionnaire avec ces informations.
    """
    try:
        conn = connect_db()
        cur = conn.cursor()

        # Nombre de comptes avec la même empreinte digitale
        cur.execute("SELECT COUNT(*) FROM users WHERE fingerprint = %s", (fingerprint,))
        same_fingerprint_count = cur.fetchone()[0]

        # Nombre d'IPs différentes utilisées avec cette empreinte
        cur.execute("SELECT COUNT(DISTINCT ip) FROM users WHERE fingerprint = %s", (fingerprint,))
        different_ips_used = cur.fetchone()[0]

        cur.close()
        conn.close()

        return {
            "same_fingerprint_count": same_fingerprint_count,
            "different_ips_used": different_ips_used
        }

    except Exception as e:
        return {"error": f"Erreur lors de l'analyse de l'historique : {str(e)}"}

# 🔹 Calcul du score de risque
def calculate_risk_score(ip_info, refund_count, payment_method, user_history):
    """
    Calcule un score de risque basé sur plusieurs critères :
    - VPN/proxy détecté → +30 points
    - Trop de remboursements (>3) → +50 points, (>5) → +70 points
    - Moyen de paiement suspect (crypto, cartes jetables) → +20 points
    - Plusieurs comptes avec la même empreinte → +40 points
    - Plusieurs commandes avec IPs différentes → +30 points
    Retourne un score de risque entre 0 et 100.
    """
    try:
        risk_score = 0

        # 🔹 Vérifier si l'IP est suspecte (VPN, Proxy, Tor)
        if ip_info.get("is_suspicious", False):
            risk_score += 30

        # 🔹 Trop de remboursements
        if refund_count > 3:
            risk_score += 50
        if refund_count > 5:
            risk_score += 70  # Augmente si remboursement excessif

        # 🔹 Moyen de paiement suspect
        if payment_method in ["crypto", "virtual_card"]:
            risk_score += 20

        # 🔹 Plusieurs comptes avec la même empreinte digitale
        if user_history.get("same_fingerprint_count", 0) > 2:
            risk_score += 40

        # 🔹 Plusieurs commandes avec des IPs différentes
        if user_history.get("different_ips_used", 0) > 3:
            risk_score += 30

        return min(risk_score, 100)  # Le score est limité à 100 max

    except Exception as e:
        return f"Erreur lors du calcul du score de risque: {str(e)}"

# 🔹 Insertion des données dans PostgreSQL
def insert_user(ip, user_agent, fingerprint, refund_count, risk_score):
    """
    Insère un utilisateur dans la base PostgreSQL.
    """
    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (ip, user_agent, fingerprint, refund_count, risk_score)
            VALUES (%s, %s, %s, %s, %s)
        """, (ip, user_agent, fingerprint, refund_count, risk_score))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion en base : {e}")

