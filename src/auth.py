"""
Çok Kullanıcılı Kimlik Doğrulama Modülü
- SQLite veritabanı ile kullanıcı yönetimi
- bcrypt ile güvenli şifre hashleme
- Kullanıcı başına izole veri klasörü
"""
import sqlite3
import bcrypt
import uuid
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "users.db"
USERS_DIR = DATA_DIR / "users"

DATA_DIR.mkdir(parents=True, exist_ok=True)
USERS_DIR.mkdir(parents=True, exist_ok=True)


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Kullanıcı tablosunu oluşturur (yoksa)."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     TEXT PRIMARY KEY,
                username    TEXT UNIQUE NOT NULL,
                email       TEXT,
                pw_hash     TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now')),
                last_login  TEXT
            )
        """)
        conn.commit()
    logger.info("Kullanıcı veritabanı hazır.")


def get_user_data_dir(user_id: str) -> Path:
    """Kullanıcıya özel veri klasörünü döner ve oluşturur."""
    user_dir = USERS_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def register_user(username: str, password: str, email: str = "") -> Dict:
    """
    Yeni kullanıcı kaydeder.
    Dönüş: {"success": bool, "user_id": str, "message": str}
    """
    username = username.strip().lower()

    if len(username) < 3:
        return {"success": False, "user_id": None, "message": "Kullanıcı adı en az 3 karakter olmalıdır."}
    if len(password) < 6:
        return {"success": False, "user_id": None, "message": "Şifre en az 6 karakter olmalıdır."}
    if not username.replace("_", "").replace(".", "").isalnum():
        return {"success": False, "user_id": None, "message": "Kullanıcı adı yalnızca harf, rakam, _ ve . içerebilir."}

    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user_id = str(uuid.uuid4()).replace("-", "")[:16]

    try:
        with _get_connection() as conn:
            conn.execute(
                "INSERT INTO users (user_id, username, email, pw_hash) VALUES (?, ?, ?, ?)",
                (user_id, username, email.strip(), pw_hash)
            )
            conn.commit()

        # Kullanıcıya özel klasörü oluştur
        get_user_data_dir(user_id)
        logger.info(f"Yeni kullanıcı kaydedildi: {username} (ID: {user_id})")
        return {"success": True, "user_id": user_id, "username": username, "message": "Kayıt başarılı!"}

    except sqlite3.IntegrityError:
        return {"success": False, "user_id": None, "message": f"'{username}' kullanıcı adı zaten alınmış."}
    except Exception as e:
        logger.error(f"Kayıt hatası: {e}")
        return {"success": False, "user_id": None, "message": "Kayıt sırasında bir hata oluştu."}


def login_user(username: str, password: str) -> Dict:
    """
    Kullanıcı girişini doğrular.
    Dönüş: {"success": bool, "user_id": str, "username": str, "message": str}
    """
    username = username.strip().lower()

    try:
        with _get_connection() as conn:
            row = conn.execute(
                "SELECT user_id, username, pw_hash FROM users WHERE username = ?",
                (username,)
            ).fetchone()

        if row is None:
            return {"success": False, "user_id": None, "message": "Kullanıcı adı veya şifre hatalı."}

        pw_match = bcrypt.checkpw(password.encode("utf-8"), row["pw_hash"].encode("utf-8"))
        if not pw_match:
            return {"success": False, "user_id": None, "message": "Kullanıcı adı veya şifre hatalı."}

        # Son giriş zamanını güncelle
        with _get_connection() as conn:
            conn.execute(
                "UPDATE users SET last_login = datetime('now') WHERE user_id = ?",
                (row["user_id"],)
            )
            conn.commit()

        logger.info(f"Giriş başarılı: {username}")
        return {
            "success": True,
            "user_id": row["user_id"],
            "username": row["username"],
            "message": f"Hoş geldin, {row['username']}!"
        }

    except Exception as e:
        logger.error(f"Giriş hatası: {e}")
        return {"success": False, "user_id": None, "message": "Giriş sırasında bir hata oluştu."}


def get_user_by_id(user_id: str) -> Optional[Dict]:
    """user_id ile kullanıcı bilgilerini getirir."""
    try:
        with _get_connection() as conn:
            row = conn.execute(
                "SELECT user_id, username, email, created_at, last_login FROM users WHERE user_id = ?",
                (user_id,)
            ).fetchone()
        if row:
            return dict(row)
        return None
    except Exception as e:
        logger.error(f"Kullanıcı getirme hatası: {e}")
        return None


def list_users() -> list:
    """Tüm kullanıcıları listeler (admin amaçlı)."""
    try:
        with _get_connection() as conn:
            rows = conn.execute(
                "SELECT user_id, username, email, created_at, last_login FROM users ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Kullanıcı listesi hatası: {e}")
        return []


# Modül yüklendiğinde veritabanını başlat
init_db()
