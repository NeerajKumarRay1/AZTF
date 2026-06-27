import os
import jwt
import bcrypt
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
import database

# Load environment configuration
load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET", "ngfw_super_secret_key")
ALGORITHM = "HS256"

# Default users to seed
DEFAULT_USERS = [
    {"username": "admin", "password": "password123", "role": "Admin"},
    {"username": "analyst", "password": "password123", "role": "Analyst"},
    {"username": "viewer", "password": "password123", "role": "Viewer"}
]

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        print("JWT Error: Token has expired")
        return None
    except jwt.InvalidTokenError:
        print("JWT Error: Invalid token")
        return None

def verify_role(payload: dict, required_role: str) -> bool:
    role_priority = {"Admin": 3, "Analyst": 2, "Viewer": 1}
    user_role = payload.get("role", "Viewer")
    
    if role_priority.get(user_role, 0) >= role_priority.get(required_role, 0):
        return True
    return False

def seed_users():
    database.init_db()
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    for u in DEFAULT_USERS:
        cursor.execute("SELECT * FROM users WHERE username = ?", (u["username"],))
        if not cursor.fetchone():
            print(f"ZeroTrust: Seeding user '{u['username']}' with role '{u['role']}'...")
            pw_hash = hash_password(u["password"])
            user_id = str(uuid.uuid4())
            cursor.execute('''
            INSERT INTO users (user_id, username, password_hash, role)
            VALUES (?, ?, ?, ?)
            ''', (user_id, u["username"], pw_hash, u["role"]))
            
    conn.commit()
    conn.close()

# Seed default users on module import
seed_users()
