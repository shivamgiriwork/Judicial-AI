import sqlite3
from passlib.context import CryptContext

# --- 🛡️ MILITARY-GRADE PASSWORD SECURITY SETUP ---
# Ye tool tumhare password ko encrypt karega
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    """Password ko hash (encrypt) karta hai"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    """Check karta hai ki plain password aur hashed password match karte hain ya nahi"""
    return pwd_context.verify(plain_password, hashed_password)

# --- 🗄️ DATABASE CONNECTION ---
def get_db_connection():
    conn = sqlite3.connect('users_v2.db') # Tumhara DB file
    conn.row_factory = sqlite3.Row
    return conn

# --- 🛠️ CREATE TABLES (Agar nahi bani hain) ---
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            phone TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            dob TEXT,
            location TEXT,
            profile_pic TEXT
        )
    ''')
    conn.commit()
    conn.close()

create_tables() # File run hote hi table check karega

# --- 🟢 USER REGISTRATION (Secure) ---
def register_user(phone, password, first_name, last_name, email, dob, location):
    if check_user_exists(phone):
        return False
    
    # Password ko encrypt kar rahe hain
    hashed_pw = hash_password(password)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 🛡️ SQL INJECTION PROTECTED (Using '?')
        cursor.execute('''
            INSERT INTO users (phone, password, first_name, last_name, email, dob, location)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (phone, hashed_pw, first_name, last_name, email, dob, location))
        conn.commit()
        return True
    except Exception as e:
        print(f"DB Error: {e}")
        return False
    finally:
        conn.close()

# --- 🔐 LOGIN VERIFICATION (Secure) ---
def check_login(phone, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    # 🛡️ SQL INJECTION PROTECTED
    cursor.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    user = cursor.fetchone()
    conn.close()
    
    # Check if user exists AND password is correct
    if user and verify_password(password, user['password']):
        return (user['first_name'], user['last_name'], user['profile_pic'])
    return None

# --- 🔍 CHECK IF USER EXISTS ---
def check_user_exists(phone):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT phone FROM users WHERE phone = ?", (phone,))
    user = cursor.fetchone()
    conn.close()
    return user is not None

# --- 👤 GET USER DETAILS ---
def get_full_user_details(phone):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, last_name, email, dob, location, phone, profile_pic FROM users WHERE phone = ?", (phone,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return tuple(user)
    return None

# --- ⚙️ UPDATE PROFILE ---
def update_user_profile(phone, first_name, last_name, email, dob):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET first_name = ?, last_name = ?, email = ?, dob = ?
        WHERE phone = ?
    ''', (first_name, last_name, email, dob, phone))
    conn.commit()
    conn.close()
    return True

# --- 🔑 RESET PASSWORD (Secure) ---
def reset_password(phone, new_password):
    hashed_pw = hash_password(new_password)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password = ? WHERE phone = ?", (hashed_pw, phone))
    conn.commit()
    conn.close()
    return True

# --- 🖼️ UPDATE PROFILE PIC ---
def update_profile_picture(phone, pic_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET profile_pic = ? WHERE phone = ?", (pic_data, phone))
    conn.commit()
    conn.close()
    return True