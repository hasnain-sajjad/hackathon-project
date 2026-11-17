import hashlib
import os
import secrets
import json
from datetime import datetime, timedelta
from app.database import db_transaction, get_db

DEMO_ACCOUNTS = [
    {
        "id": "ADMIN",
        "name": "Admin",
        "email": "admin@novaworks.example",
        "role": "ADMIN",
        "specialization": "Administrator",
        "skills": ["Company overview", "transcript creation"],
        "password": "Demo123!"
    },
    {
        "id": "PM01",
        "name": "Ayesha Khan",
        "email": "ayesha@novaworks.example",
        "role": "MANAGER",
        "specialization": "Manager / Web PM",
        "skills": ["Web projects", "client coordination"],
        "password": "Demo123!"
    },
    {
        "id": "PM02",
        "name": "Bilal Ahmed",
        "email": "bilal@novaworks.example",
        "role": "MANAGER",
        "specialization": "Manager / Mobile PM",
        "skills": ["Mobile projects", "delivery planning"],
        "password": "Demo123!"
    },
    {
        "id": "PM03",
        "name": "Hina Malik",
        "email": "hina@novaworks.example",
        "role": "MANAGER",
        "specialization": "Manager / AI PM",
        "skills": ["AI projects", "requirement review"],
        "password": "Demo123!"
    },
    {
        "id": "DEV01",
        "name": "Ali Raza",
        "email": "ali@novaworks.example",
        "role": "AGENT",
        "specialization": "Agent / Full-Stack",
        "skills": ["React", "frontend integration"],
        "password": "Demo123!"
    },
    {
        "id": "DEV02",
        "name": "Hamza Shah",
        "email": "hamza@novaworks.example",
        "role": "AGENT",
        "specialization": "Agent / Full-Stack",
        "skills": ["Node.js", "databases", "APIs"],
        "password": "Demo123!"
    },
    {
        "id": "DEV03",
        "name": "Sara Noor",
        "email": "sara@novaworks.example",
        "role": "AGENT",
        "specialization": "Agent / App Developer",
        "skills": ["Flutter", "mobile UI"],
        "password": "Demo123!"
    },
    {
        "id": "DEV04",
        "name": "Usman Tariq",
        "email": "usman@novaworks.example",
        "role": "AGENT",
        "specialization": "Agent / App Developer",
        "skills": ["Flutter", "integration", "testing"],
        "password": "Demo123!"
    },
    {
        "id": "DEV05",
        "name": "Zain Abbas",
        "email": "zain@novaworks.example",
        "role": "AGENT",
        "specialization": "Agent / AI Developer",
        "skills": ["LLMs", "extraction", "prompts"],
        "password": "Demo123!"
    },
    {
        "id": "DEV06",
        "name": "Maryam Asif",
        "email": "maryam@novaworks.example",
        "role": "AGENT",
        "specialization": "Agent / AI Developer",
        "skills": ["Retrieval", "document processing"],
        "password": "Demo123!"
    }
]

def hash_password(password: str) -> str:
    """Secure PBKDF2-HMAC-SHA256 password hashing with random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${key.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies a plain password against the stored salt$hash credential."""
    try:
        salt, key_hex = stored_hash.split("$", 1)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return secrets.compare_digest(key.hex(), key_hex)
    except Exception:
        return False

def seed_demo_users():
    """Inserts or updates the 10 supplied demo accounts. Re-running will not duplicate users."""
    count = 0
    with db_transaction() as conn:
        cursor = conn.cursor()
        for acc in DEMO_ACCOUNTS:
            pwd_hash = hash_password(acc["password"])
            skills_json = json.dumps(acc["skills"])
            
            # Check if email exists
            cursor.execute("SELECT id FROM users WHERE email = ?", (acc["email"],))
            row = cursor.fetchone()
            if row:
                cursor.execute("""
                    UPDATE users 
                    SET name = ?, password_hash = ?, role = ?, specialization = ?, skills = ?
                    WHERE email = ?
                """, (acc["name"], pwd_hash, acc["role"], acc["specialization"], skills_json, acc["email"]))
            else:
                cursor.execute("""
                    INSERT INTO users (id, name, email, password_hash, role, specialization, skills)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (acc["id"], acc["name"], acc["email"], pwd_hash, acc["role"], acc["specialization"], skills_json))
            count += 1
    print(f"[Auth] Seeded {count} demo users successfully.")
    return count

def authenticate_user(email: str, password: str):
    """Finds user by email and verifies password. Returns user dict or None."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email.strip(),))
        row = cursor.fetchone()
        if not row:
            return None
        
        user_dict = dict(row)
        if not verify_password(password, user_dict["password_hash"]):
            return None
        
        # Don't expose password hash
        user_dict.pop("password_hash", None)
        user_dict["skills"] = json.loads(user_dict.get("skills") or "[]")
        return user_dict
    finally:
        conn.close()

def create_session(user_id: str) -> str:
    """Creates a secure session token valid for 7 days."""
    token = secrets.token_hex(32)
    expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()
    with db_transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)", 
                       (token, user_id, expires_at))
    return token

def get_current_user(token: str):
    """Retrieves authenticated user from session token if valid and not expired."""
    if not token:
        return None
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.token, s.expires_at, u.id, u.name, u.email, u.role, u.specialization, u.skills
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ?
        """, (token,))
        row = cursor.fetchone()
        if not row:
            return None
        
        # Check expiry
        expires_at_str = row["expires_at"]
        try:
            exp = datetime.fromisoformat(expires_at_str)
            if datetime.utcnow() > exp:
                # Expired session
                cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
                conn.commit()
                return None
        except Exception:
            pass

        user = {
            "id": row["id"],
            "name": row["name"],
            "email": row["email"],
            "role": row["role"],
            "specialization": row["specialization"],
            "skills": json.loads(row["skills"] or "[]")
        }
        return user
    finally:
        conn.close()

def delete_session(token: str):
    """Logs out by deleting the session token."""
    with db_transaction() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
