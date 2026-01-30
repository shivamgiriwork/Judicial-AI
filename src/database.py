import sqlite3
import bcrypt
from datetime import date

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Table for security and search limits
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (phone TEXT PRIMARY KEY, password BLOB, name TEXT, 
                  limit_count INTEGER, last_date TEXT, is_premium BOOLEAN)''')
    conn.commit()
    conn.close()

def register_user(phone, password, name):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?, 0, ?, 0)", 
                  (phone, hashed, name, str(date.today())))
        conn.commit()
        return True
    except: return False
    finally: conn.close()

init_db()