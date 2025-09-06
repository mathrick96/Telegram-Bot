import logging
import sqlite3

from .paths import DB_PATH


def log_all_users():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """
                SELECT user_id, language, level, delivery_hour, timezone, last_sent, configured
                FROM users
                ORDER BY user_id
                """
            )
            rows = cur.fetchall()
            logging.info("DB dump: %d row(s) in users.", len(rows))
            for r in rows:
                logging.info(
                    "user_id=%s | language=%s | level=%s | delivery_hour=%s | timezone=%s | last_sent=%s | configured=%s",
                    r["user_id"],
                    r["language"],
                    r["level"],
                    r["delivery_hour"],
                    r["timezone"],
                    r["last_sent"],
                    r["configured"],
                )
            return len(rows)
    except Exception as e:
        logging.exception("DB dump failed: %s", e)
        return None


def get_user_data(user_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            if row:
                logging.info(f"Retrieved user_id {user_id} successfully.")
                return True, dict(row)
            else:
                logging.warning(f"No user found with user_id {user_id}.")
                return False, None
    except Exception as e:
        logging.error(f"Error retrieving user_id {user_id}: {e}")
        return False, None


def create_new_user(user_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR IGNORE INTO users
                (user_id, configured)
                VALUES (?, 0)
                """,
                (user_id,),
            )
            conn.commit()
            if cur.rowcount > 0:
                logging.info(f"Inserted new user_id {user_id} successfully.")
                return True
            else:
                logging.warning(f"User_id {user_id} already exists. No insertion.")
                return False
    except Exception as e:
        logging.error(f"Error inserting user_id {user_id}: {e}")
        return False


def save_new_user(user_data):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR IGNORE INTO users
                (user_id, language, level, delivery_hour, timezone, last_sent, configured)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                user_data,
            )
            conn.commit()
            if cur.rowcount > 0:
                logging.info(f"Inserted new user_id {user_data[0]} successfully.")
                return True
            else:
                logging.warning(f"User_id {user_data[0]} already exists. No insertion.")
                return False
    except Exception as e:
        logging.error(f"Error inserting user_id {user_data[0]}: {e}")
        return False


def update_user(
    user_id,
    language=None,
    level=None,
    delivery_hour=None,
    timezone=None,
    configured=None,
    last_sent=None,
    pending_delivery_time=None,
):
    fields, values = [], []
    if language is not None:
        fields.append("language = ?")
        values.append(language)
    if level is not None:
        fields.append("level = ?")
        values.append(level)
    if delivery_hour is not None:
        fields.append("delivery_hour = ?")
        values.append(delivery_hour)
    if timezone is not None:
        fields.append("timezone = ?")
        values.append(timezone)
    if configured is not None:
        fields.append("configured = ?")
        values.append(configured)
    if last_sent is not None:
        fields.append("last_sent = ?")
        values.append(last_sent)
    if not fields:
        return False  # nothing to update
    values.append(user_id)
    db_query = f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?"
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute(db_query, values)
            conn.commit()
            if cur.rowcount > 0:
                logging.info(f"Updated user_id {user_id} successfully.")
                return True
            else:
                logging.warning(
                    f"No user found with user_id {user_id}. Update skipped."
                )
                return False
    except Exception as e:
        logging.error(f"Error updating user_id {user_id}: {e}")
        return False


def delete_user(user_id):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()
            if cur.rowcount > 0:
                logging.info(f"Deleted user_id {user_id} successfully.")
                return True
            else:
                logging.warning(
                    f"No user found with user_id {user_id}. Deletion skipped."
                )
                return False
    except Exception as e:
        logging.error(f"Error deleting user_id {user_id}: {e}")
        return False
    
def migrate_last_sent_to_timestamp():
    """Ensure all last_sent entries include a time component."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA user_version")
            version = cur.fetchone()[0]
            if version < 1:
                cur.execute(
                    """
                    UPDATE users
                    SET last_sent = last_sent || 'T00:00:00'
                    WHERE last_sent IS NOT NULL AND length(last_sent) = 10
                    """
                )
                cur.execute("PRAGMA user_version = 1")
                conn.commit()
                logging.info("Migrated last_sent values to include timestamps.")
    except Exception as e:
        logging.error(f"Error during migration: {e}")
