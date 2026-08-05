"""Postgres (Supabase) persistence layer with SQLite local fallback support.
"""
import hashlib
import os
import secrets
import sqlite3
import threading
import bcrypt
from datetime import datetime, timedelta, timezone

import config

def _row_to_dict(cursor, row):
    if not row:
        return None
    if isinstance(row, dict):
        return row
    if hasattr(row, 'keys'):
        try:
            return dict(zip(row.keys(), row))
        except Exception:
            pass
    if hasattr(cursor, 'description') and cursor.description:
        colnames = [col[0] for col in cursor.description]
        try:
            return dict(zip(colnames, row))
        except Exception:
            pass
    return row

class SQLiteCursorWrapper:
    def __init__(self, cursor):
        self._cursor = cursor
    def execute(self, sql, params=()):
        sql = sql.replace('%s', '?')
        return self._cursor.execute(sql, params)
    def fetchone(self):
        row = self._cursor.fetchone()
        return _row_to_dict(self._cursor, row)
    def fetchall(self):
        rows = self._cursor.fetchall()
        return [_row_to_dict(self._cursor, r) for r in rows]
    @property
    def description(self):
        return self._cursor.description
    @property
    def rowcount(self):
        return self._cursor.rowcount

class SQLiteConnWrapper:
    def __init__(self, conn):
        self._conn = conn
    def cursor(self, *args, **kwargs):
        c = self._conn.cursor()
        return SQLiteCursorWrapper(c)
    def commit(self):
        return self._conn.commit()
    def rollback(self):
        return self._conn.rollback()
    def close(self):
        return self._conn.close()
    def execute(self, sql, params=()):
        sql = sql.replace('%s', '?')
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return SQLiteCursorWrapper(cur)

class Database:
    def __init__(self):
        self.is_sqlite = False
        db_url = getattr(config, 'DATABASE_URL', '') or ''
        
        if db_url.startswith('sqlite') or not db_url or 'postgres' not in db_url:
            self.is_sqlite = True
            clean_path = db_url.replace('sqlite:///', '').replace('sqlite://', '')
            if not clean_path:
                clean_path = os.path.join(os.path.dirname(__file__), 'data', 'chatbot.db')
            os.makedirs(os.path.dirname(os.path.abspath(clean_path)), exist_ok=True)
            self.sqlite_path = clean_path
            self.init_db()
        else:
            import psycopg
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool

            self._connect_kwargs = {
                'connect_timeout': 10,
                'keepalives': 1,
                'keepalives_idle': 30,
                'keepalives_interval': 10,
                'keepalives_count': 3,
            }

            def _configure(conn):
                conn.execute("SET statement_timeout = '15s'")
                conn.commit()

            self._configure_cb = _configure
            self._pool = None
            self._pool_pid = None
            self._pool_lock = threading.Lock()

    def _get_pool(self):
        if self.is_sqlite:
            return None
        from psycopg_pool import ConnectionPool
        pool = self._pool
        if pool is not None and self._pool_pid == os.getpid():
            return pool
        with self._pool_lock:
            pid = os.getpid()
            if self._pool is not None and self._pool_pid == pid:
                return self._pool
            self._pool = ConnectionPool(
                config.DATABASE_URL, min_size=1, max_size=3, open=True,
                kwargs=self._connect_kwargs, configure=self._configure_cb,
                check=ConnectionPool.check_connection,
                timeout=10, max_lifetime=300, max_idle=60,
            )
            self._pool_pid = pid
            return self._pool

    def get_pool_stats(self):
        if self.is_sqlite:
            return {'type': 'sqlite', 'pid': os.getpid(), 'path': getattr(self, 'sqlite_path', '')}
        try:
            pool = self._get_pool()
            stats = dict(pool.get_stats())
            stats['pid'] = os.getpid()
            stats['max_size_cfg'] = pool.max_size
            return stats
        except Exception as exc:
            return {'error': str(exc)[:100], 'pid': os.getpid()}

    def get_connection(self):
        if self.is_sqlite:
            raw_conn = sqlite3.connect(self.sqlite_path)
            raw_conn.row_factory = sqlite3.Row
            return SQLiteConnWrapper(raw_conn)
        return self._get_pool().getconn()

    def release_connection(self, conn):
        if self.is_sqlite:
            try:
                conn.close()
            except Exception:
                pass
            return

        import psycopg
        try:
            if conn.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
                conn.rollback()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
        self._get_pool().putconn(conn)

    def init_db(self):
        conn = self.get_connection()
        try:
            if self.is_sqlite:
                c = conn.cursor()
                c.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                c.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        language TEXT DEFAULT 'en',
                        is_archived BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                c.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        conversation_id TEXT NOT NULL,
                        sender TEXT NOT NULL,
                        text TEXT NOT NULL,
                        language TEXT DEFAULT 'en',
                        tokens_used INTEGER DEFAULT 0,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                c.execute('''
                    CREATE TABLE IF NOT EXISTS api_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        endpoint TEXT NOT NULL,
                        tokens_used INTEGER DEFAULT 0,
                        cost REAL DEFAULT 0,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                c.execute('''
                    CREATE TABLE IF NOT EXISTS personas (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        system_prompt TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                c.execute('''
                    CREATE TABLE IF NOT EXISTS password_reset_tokens (
                        token TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        used BOOLEAN DEFAULT FALSE,
                        expires_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                c.execute('''
                    CREATE TABLE IF NOT EXISTS pending_registrations (
                        email TEXT PRIMARY KEY,
                        username TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        otp_code TEXT NOT NULL,
                        attempts INTEGER DEFAULT 0,
                        expires_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
            else:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id VARCHAR(255) PRIMARY KEY,
                        username VARCHAR(255) UNIQUE NOT NULL,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS conversations (
                        id VARCHAR(255) PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        title TEXT NOT NULL,
                        language VARCHAR(10) DEFAULT 'en',
                        is_archived BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS messages (
                        id VARCHAR(255) PRIMARY KEY,
                        conversation_id VARCHAR(255) NOT NULL,
                        sender VARCHAR(50) NOT NULL,
                        text TEXT NOT NULL,
                        language VARCHAR(10) DEFAULT 'en',
                        tokens_used INTEGER DEFAULT 0,
                        timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS api_usage (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        endpoint VARCHAR(255) NOT NULL,
                        tokens_used INTEGER DEFAULT 0,
                        cost REAL DEFAULT 0,
                        timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS personas (
                        id VARCHAR(255) PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        system_prompt TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS password_reset_tokens (
                        token VARCHAR(255) PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        used BOOLEAN DEFAULT FALSE,
                        expires_at TIMESTAMPTZ NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS pending_registrations (
                        email VARCHAR(255) PRIMARY KEY,
                        username VARCHAR(255) NOT NULL,
                        password_hash TEXT NOT NULL,
                        otp_code VARCHAR(10) NOT NULL,
                        attempts INTEGER DEFAULT 0,
                        expires_at TIMESTAMPTZ NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS memory_messages (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        role VARCHAR(50) NOT NULL,
                        content TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE INDEX IF NOT EXISTS idx_memory_messages_user ON memory_messages(user_id, id);
                    CREATE TABLE IF NOT EXISTS user_facts (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        fact_key VARCHAR(255) NOT NULL,
                        fact_value TEXT NOT NULL,
                        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, fact_key)
                    );
                    CREATE INDEX IF NOT EXISTS idx_user_facts_user ON user_facts(user_id);
                ''')
                conn.commit()
        finally:
            self.release_connection(conn)

    # USER MANAGEMENT
    def create_user(self, username, email, password):
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        return self._insert_user(username, email, password_hash)

    def _insert_user(self, username, email, password_hash, user_id=None):
        if not user_id:
            user_id = hashlib.md5(f"{username}{datetime.now()}".encode()).hexdigest()
        conn = self.get_connection()
        try:
            c = conn.cursor()
            param_placeholder = '?' if self.is_sqlite else '%s'
            c.execute(f'''
                INSERT INTO users (id, username, email, password_hash)
                VALUES ({param_placeholder}, {param_placeholder}, {param_placeholder}, {param_placeholder})
            ''', (user_id, username, email, password_hash))
            conn.commit()
            return user_id
        except Exception:
            return None
        finally:
            self.release_connection(conn)

    def get_user(self, username):
        conn = self.get_connection()
        try:
            c = conn.cursor()
            param = '?' if self.is_sqlite else '%s'
            c.execute(f'SELECT * FROM users WHERE LOWER(username) = LOWER({param}) OR LOWER(email) = LOWER({param})', (username, username))
            return _row_to_dict(c, c.fetchone())
        finally:
            self.release_connection(conn)

    def get_user_by_id(self, user_id):
        conn = self.get_connection()
        try:
            c = conn.cursor()
            param = '?' if self.is_sqlite else '%s'
            c.execute(f'SELECT * FROM users WHERE id = {param}', (user_id,))
            return _row_to_dict(c, c.fetchone())
        finally:
            self.release_connection(conn)

    def verify_password(self, stored_hash, password):
        """Verify password against stored hash. stored_hash is None for
        OAuth-only accounts (no password was ever set) - no password can
        match that, so fail closed instead of crashing on None.encode()."""
        if not stored_hash:
            return False
        return bcrypt.checkpw(password.encode(), stored_hash.encode())

    def update_password(self, user_id, new_password):
        password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        conn = self.get_connection()
        try:
            c = conn.cursor()
            param = '?' if self.is_sqlite else '%s'
            now_sql = "CURRENT_TIMESTAMP" if self.is_sqlite else "NOW()"
            c.execute(f'''
                UPDATE users SET password_hash = {param}, updated_at = {now_sql} WHERE id = {param}
            ''', (password_hash, user_id))
            conn.commit()
            return c.rowcount > 0
        finally:
            self.release_connection(conn)

    def delete_user(self, user_id):
        conn = self.get_connection()
        try:
            c = conn.cursor()
            param = '?' if self.is_sqlite else '%s'
            c.execute(f'''
                DELETE FROM messages WHERE conversation_id IN 
                (SELECT id FROM conversations WHERE user_id = {param})
            ''', (user_id,))
            c.execute(f'DELETE FROM conversations WHERE user_id = {param}', (user_id,))
            c.execute(f'DELETE FROM api_usage WHERE user_id = {param}', (user_id,))
            c.execute(f'DELETE FROM personas WHERE user_id = {param}', (user_id,))
            c.execute(f'DELETE FROM password_reset_tokens WHERE user_id = {param}', (user_id,))
            c.execute(f'DELETE FROM users WHERE id = {param}', (user_id,))
            conn.commit()
            return c.rowcount > 0
        finally:
            self.release_connection(conn)

    def get_user_by_email(self, email):
        conn = self.get_connection()
        try:
            c = conn.cursor()
            param = '?' if self.is_sqlite else '%s'
            c.execute(f'SELECT * FROM users WHERE email = {param}', (email,))
            return _row_to_dict(c, c.fetchone())
        finally:
            self.release_connection(conn)

    MAX_OTP_ATTEMPTS = 5

    # PENDING REGISTRATION / OTP
    def create_pending_registration(self, username, email, password, otp_code, ttl_minutes=15):
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        conn = self.get_connection()
        try:
            c = conn.cursor()
            param = '?' if self.is_sqlite else '%s'
            c.execute(f'DELETE FROM pending_registrations WHERE email = {param}', (email,))
            c.execute(f'''
                INSERT INTO pending_registrations (email, username, password_hash, otp_code, expires_at)
                VALUES ({param}, {param}, {param}, {param}, {param})
            ''', (email, username, password_hash, otp_code, expires_at))
            conn.commit()
            return True
        finally:
            self.release_connection(conn)

    def get_pending_registration(self, email):
        conn = self.get_connection()
        try:
            c = conn.cursor()
            param = '?' if self.is_sqlite else '%s'
            c.execute(f'SELECT * FROM pending_registrations WHERE email = {param}', (email,))
            row = c.fetchone()
        finally:
            self.release_connection(conn)
        if not row:
            return None
        exp = row.get('expires_at') if isinstance(row, dict) else None
        if isinstance(exp, str):
            exp = datetime.fromisoformat(exp.replace('Z', '+00:00'))
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp and exp < datetime.now(timezone.utc):
            self.delete_pending_registration(email)
            return None
        return row

    def delete_pending_registration(self, email):
        conn = self.get_connection()
        try:
            param = '?' if self.is_sqlite else '%s'
            conn.execute(f'DELETE FROM pending_registrations WHERE email = {param}', (email,))
            conn.commit()
        finally:
            self.release_connection(conn)

    def increment_otp_attempts(self, email):
        conn = self.get_connection()
        try:
            param = '?' if self.is_sqlite else '%s'
            conn.execute(f'UPDATE pending_registrations SET attempts = attempts + 1 WHERE email = {param}', (email,))
            conn.commit()
        finally:
            self.release_connection(conn)

    # OAUTH (Google / GitHub)
    def get_user_by_oauth(self, provider, oauth_id):
        """Get user by (oauth_provider, oauth_id) pair"""
        conn = self.get_connection()
        try:
            c = conn.cursor(row_factory=dict_row)
            c.execute(
                'SELECT * FROM users WHERE oauth_provider = %s AND oauth_id = %s',
                (provider, oauth_id),
            )
            user = c.fetchone()
            return dict(user) if user else None
        finally:
            self.release_connection(conn)

    def _unique_username(self, cursor, base):
        """Derive a free username from `base` (already lowercased/sanitized
        by the caller), appending a numeric suffix on collision. Runs on the
        same connection/transaction as the insert that follows so there's no
        TOCTOU gap between checking and reserving the name."""
        candidate = base or 'user'
        suffix = 0
        while True:
            cursor.execute('SELECT 1 FROM users WHERE username = %s', (candidate,))
            if not cursor.fetchone():
                return candidate
            suffix += 1
            candidate = f"{base}{suffix}"

    def create_oauth_user(self, username, email, oauth_provider, oauth_id):
        """Create a new account with no password, identified by an OAuth
        provider + id. `username` is a suggestion - collisions are resolved
        automatically since OAuth doesn't give the user a chance to pick one
        up front."""
        user_id = hashlib.md5(f"{email}{oauth_provider}{datetime.now()}".encode()).hexdigest()
        conn = self.get_connection()
        try:
            c = conn.cursor()
            final_username = self._unique_username(c, username)
            c.execute('''
                INSERT INTO users (id, username, email, password_hash, oauth_provider, oauth_id)
                VALUES (%s, %s, %s, NULL, %s, %s)
            ''', (user_id, final_username, email, oauth_provider, oauth_id))
            conn.commit()
            return user_id
        except psycopg.errors.IntegrityError:
            conn.rollback()
            return None
        finally:
            self.release_connection(conn)

    def link_oauth_account(self, user_id, oauth_provider, oauth_id):
        """Attach an OAuth provider to an existing (password-based) account,
        so its owner can log in either way from now on."""
        conn = self.get_connection()
        try:
            c = conn.cursor()
            c.execute(
                'UPDATE users SET oauth_provider = %s, oauth_id = %s, updated_at = NOW() WHERE id = %s',
                (oauth_provider, oauth_id, user_id),
            )
            conn.commit()
            return c.rowcount > 0
        finally:
            self.release_connection(conn)

    # PASSWORD RESET
    def create_password_reset_token(self, user_id, ttl_minutes=60):
        conn = self.get_connection()
        try:
            c = conn.cursor()
            param = '?' if self.is_sqlite else '%s'
            true_val = '1' if self.is_sqlite else 'TRUE'
            false_val = '0' if self.is_sqlite else 'FALSE'
            c.execute(f'''
                UPDATE password_reset_tokens SET used = {true_val} WHERE user_id = {param} AND used = {false_val}
            ''', (user_id,))
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
            c.execute(f'''
                INSERT INTO password_reset_tokens (token, user_id, expires_at) VALUES ({param}, {param}, {param})
            ''', (token, user_id, expires_at))
            conn.commit()
            return token
        finally:
            self.release_connection(conn)

    def get_valid_reset_token(self, token):
        conn = self.get_connection()
        try:
            c = conn.cursor()
            param = '?' if self.is_sqlite else '%s'
            c.execute(f'SELECT * FROM password_reset_tokens WHERE token = {param}', (token,))
            row = _row_to_dict(c, c.fetchone())
        finally:
            self.release_connection(conn)
        if not row:
            return None
        if isinstance(row, dict) and row.get('used'):
            return None
        exp = row.get('expires_at') if isinstance(row, dict) else None
        if isinstance(exp, str):
            exp = datetime.fromisoformat(exp.replace('Z', '+00:00'))
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp and exp < datetime.now(timezone.utc):
            return None
        return row

    def mark_reset_token_used(self, token):
        conn = self.get_connection()
        try:
            param = '?' if self.is_sqlite else '%s'
            true_val = '1' if self.is_sqlite else 'TRUE'
            conn.execute(f'UPDATE password_reset_tokens SET used = {true_val} WHERE token = {param}', (token,))
            conn.commit()
        finally:
            self.release_connection(conn)

    MAX_OTP_ATTEMPTS = 5

    def create_pending_registration(self, username, email, password, otp_code, ttl_minutes=10):
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        expires_str = expires_at.strftime('%Y-%m-%d %H:%M:%S')

        conn = self.get_connection()
        try:
            c = conn.cursor()
            param = '?' if self.is_sqlite else '%s'
            c.execute(f'DELETE FROM pending_registrations WHERE email = {param}', (email,))
            c.execute(f'''
                INSERT INTO pending_registrations (email, username, password_hash, otp_code, attempts, expires_at)
                VALUES ({param}, {param}, {param}, {param}, 0, {param})
            ''', (email, username, password_hash, otp_code, expires_str))
            conn.commit()
        finally:
            self.release_connection(conn)

    def get_pending_registration(self, email):
        conn = self.get_connection()
        try:
            c = conn.cursor()
            param = '?' if self.is_sqlite else '%s'
            c.execute(f'SELECT * FROM pending_registrations WHERE email = {param}', (email,))
            row = _row_to_dict(c, c.fetchone())
            if not row:
                return None
            
            exp = row.get('expires_at') if isinstance(row, dict) else None
            if isinstance(exp, str):
                try:
                    exp = datetime.fromisoformat(exp.replace('Z', '+00:00'))
                except Exception:
                    pass
            if isinstance(exp, datetime):
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp < datetime.now(timezone.utc):
                    return None
            return row
        finally:
            self.release_connection(conn)

    def delete_pending_registration(self, email):
        conn = self.get_connection()
        try:
            param = '?' if self.is_sqlite else '%s'
            conn.execute(f'DELETE FROM pending_registrations WHERE email = {param}', (email,))
            conn.commit()
        finally:
            self.release_connection(conn)

    def increment_otp_attempts(self, email):
        conn = self.get_connection()
        try:
            param = '?' if self.is_sqlite else '%s'
            conn.execute(f'UPDATE pending_registrations SET attempts = attempts + 1 WHERE email = {param}', (email,))
            conn.commit()
        finally:
            self.release_connection(conn)

    # CONVERSATION MANAGEMENT
    def create_conversation(self, user_id, title, language='en'):
        conv_id = hashlib.md5(f"{user_id}{datetime.now()}".encode()).hexdigest()
        conn = self.get_connection()
        try:
            param = '?' if self.is_sqlite else '%s'
            conn.execute(f'''
                INSERT INTO conversations (id, user_id, title, language)
                VALUES ({param}, {param}, {param}, {param})
            ''', (conv_id, user_id, title, language))
            conn.commit()
            return conv_id
        finally:
            self.release_connection(conn)

    def get_conversations(self, user_id, limit=50):
        conn = self.get_connection()
        try:
            c = conn.cursor()
            param = '?' if self.is_sqlite else '%s'
            false_val = '0' if self.is_sqlite else 'FALSE'
            c.execute(f'''
                SELECT * FROM conversations
                WHERE user_id = {param} AND is_archived = {false_val}
                ORDER BY updated_at DESC
                LIMIT {param}
            ''', (user_id, limit))
            rows = c.fetchall()
            return [_row_to_dict(c, r) for r in rows]
        finally:
            self.release_connection(conn)

    def update_conversation_title(self, conv_id, title):
        conn = self.get_connection()
        try:
            param = '?' if self.is_sqlite else '%s'
            now_sql = "CURRENT_TIMESTAMP" if self.is_sqlite else "NOW()"
            conn.execute(f'''
                UPDATE conversations
                SET title = {param}, updated_at = {now_sql}
                WHERE id = {param}
            ''', (title, conv_id))
            conn.commit()
        finally:
            self.release_connection(conn)

    # MESSAGE MANAGEMENT
    def add_message(self, conv_id, sender, text, language='en', tokens=0):
        msg_id = hashlib.md5(f"{conv_id}{datetime.now()}".encode()).hexdigest()
        conn = self.get_connection()
        try:
            c = conn.cursor()
            param = '?' if self.is_sqlite else '%s'
            now_sql = "CURRENT_TIMESTAMP" if self.is_sqlite else "NOW()"
            c.execute(f'''
                INSERT INTO messages (id, conversation_id, sender, text, language, tokens_used)
                VALUES ({param}, {param}, {param}, {param}, {param}, {param})
            ''', (msg_id, conv_id, sender, text, language, tokens))
            c.execute(f'''
                UPDATE conversations
                SET updated_at = {now_sql}
                WHERE id = {param}
            ''', (conv_id,))
            conn.commit()
            return msg_id
        finally:
            self.release_connection(conn)

    def get_messages(self, conv_id, limit=100):
        conn = self.get_connection()
        try:
            c = conn.cursor()
            param = '?' if self.is_sqlite else '%s'
            c.execute(f'''
                SELECT * FROM messages
                WHERE conversation_id = {param}
                ORDER BY timestamp ASC
                LIMIT {param}
            ''', (conv_id, limit))
            rows = c.fetchall()
            return [_row_to_dict(c, r) for r in rows]
        finally:
            self.release_connection(conn)

    def get_conversation_history(self, conv_id, max_tokens=4000):
        messages = self.get_messages(conv_id, limit=50)
        history = []
        token_count = 0
        for msg in messages:
            msg_tokens = len(msg['text'].split())
            if token_count + msg_tokens > max_tokens:
                break
            history.append({
                'role': 'user' if msg['sender'] == 'user' else 'assistant',
                'content': msg['text']
            })
            token_count += msg_tokens
        return history

    # ANALYTICS
    def log_api_usage(self, user_id, endpoint, tokens_used=0, cost=0):
        conn = self.get_connection()
        try:
            param = '?' if self.is_sqlite else '%s'
            conn.execute(f'''
                INSERT INTO api_usage (user_id, endpoint, tokens_used, cost)
                VALUES ({param}, {param}, {param}, {param})
            ''', (user_id, endpoint, tokens_used, cost))
            conn.commit()
        finally:
            self.release_connection(conn)

    def get_user_stats(self, user_id):
        conn = self.get_connection()
        try:
            c = conn.cursor()
            param = '?' if self.is_sqlite else '%s'
            false_val = '0' if self.is_sqlite else 'FALSE'
            c.execute(f'''
                SELECT SUM(tokens_used) as total_tokens FROM api_usage
                WHERE user_id = {param}
            ''', (user_id,))
            row = _row_to_dict(c, c.fetchone())
            total_tokens = (row.get('total_tokens') if isinstance(row, dict) else 0) or 0

            c.execute(f'''
                SELECT COUNT(*) as count FROM conversations
                WHERE user_id = {param} AND is_archived = {false_val}
            ''', (user_id,))
            row_c = _row_to_dict(c, c.fetchone())
            total_conversations = (row_c.get('count') if isinstance(row_c, dict) else 0) or 0

            return {
                'total_tokens': total_tokens,
                'total_conversations': total_conversations
            }
        finally:
            self.release_connection(conn)

    # PERSONA MANAGEMENT
    def create_persona(self, user_id, name, system_prompt):
        persona_id = hashlib.md5(f"{user_id}{name}{datetime.now()}".encode()).hexdigest()
        conn = self.get_connection()
        try:
            param = '?' if self.is_sqlite else '%s'
            conn.execute(f'''
                INSERT INTO personas (id, user_id, name, system_prompt)
                VALUES ({param}, {param}, {param}, {param})
            ''', (persona_id, user_id, name, system_prompt))
            conn.commit()
            return persona_id
        finally:
            self.release_connection(conn)

    def list_personas(self, user_id):
        conn = self.get_connection()
        try:
            c = conn.cursor()
            param = '?' if self.is_sqlite else '%s'
            c.execute(f'''
                SELECT * FROM personas WHERE user_id = {param} ORDER BY created_at ASC
            ''', (user_id,))
            rows = c.fetchall()
            return [_row_to_dict(c, r) for r in rows]
        finally:
            self.release_connection(conn)

    def get_persona(self, persona_id, user_id):
        conn = self.get_connection()
        try:
            c = conn.cursor()
            param = '?' if self.is_sqlite else '%s'
            c.execute(f'''
                SELECT * FROM personas WHERE id = {param} AND user_id = {param}
            ''', (persona_id, user_id))
            return _row_to_dict(c, c.fetchone())
        finally:
            self.release_connection(conn)

    def update_persona(self, persona_id, user_id, name, system_prompt):
        if not self.get_persona(persona_id, user_id):
            return False
        conn = self.get_connection()
        try:
            param = '?' if self.is_sqlite else '%s'
            now_sql = "CURRENT_TIMESTAMP" if self.is_sqlite else "NOW()"
            conn.execute(f'''
                UPDATE personas
                SET name = {param}, system_prompt = {param}, updated_at = {now_sql}
                WHERE id = {param} AND user_id = {param}
            ''', (name, system_prompt, persona_id, user_id))
            conn.commit()
            return True
        finally:
            self.release_connection(conn)

    def delete_persona(self, persona_id, user_id):
        if not self.get_persona(persona_id, user_id):
            return False
        conn = self.get_connection()
        try:
            param = '?' if self.is_sqlite else '%s'
            conn.execute(f'DELETE FROM personas WHERE id = {param} AND user_id = {param}', (persona_id, user_id))
            conn.commit()
            return True
        finally:
            self.release_connection(conn)

db = Database()
