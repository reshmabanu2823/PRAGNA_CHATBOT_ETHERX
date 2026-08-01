"""Postgres (Supabase) persistence layer.

Was SQLite on local disk until it turned out every Render deploy/restart
wiped the database - the container filesystem isn't persistent, and the
committed backend/data/chatbot.db (an accidental git-tracked artifact from
before *.db was added to .gitignore) is what every fresh container started
from. Schema lives in Supabase migrations, not here - init_db() only
verifies connectivity, it doesn't create tables.

get_connection()/release_connection() check a connection out of / back
into a pool, mirroring the old sqlite3.connect()/conn.close() call shape
so app.py and chat_management_api.py - which both call db.get_connection()
directly rather than going through a Database method - needed the smallest
possible change (release_connection() instead of close(), %s instead of
?, plus a dict_row cursor wherever the code reads columns by name). A
context-manager-only get_connection() would have been cleaner in
isolation, but broken every one of those call sites.

DATABASE_URL must point at Supabase's Session pooler (port 5432), not the
Transaction pooler (port 6543) - Supabase's own docs say Transaction mode
isn't meant to sit under an external connection pool like this one, and in
production that combination surfaced as intermittent
"SSL SYSCALL error: EOF detected" / "decryption failed" errors once a
pooled connection had sat idle for a while and PgBouncer recycled the
underlying backend connection out from under it. Session mode dedicates a
real backend connection for the lifetime of ours, which is what a
persistent client-side pool actually needs.
"""
import hashlib
import os
import secrets
import threading
import bcrypt
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

import config

class Database:
    def __init__(self):
        if not config.DATABASE_URL:
            raise RuntimeError(
                'DATABASE_URL is not set. Postgres (Supabase) is required - '
                'there is no SQLite fallback (that mode silently lost all '
                'data on every deploy). Set DATABASE_URL to a Supabase '
                'connection string (Session Pooler, port 5432).'
            )
        # min_size=1 keeps this cheap at idle; max_size covers a handful of
        # concurrent requests per gunicorn worker without needing to tune it.
        #
        # check=ConnectionPool.check_connection pings a connection before
        # handing it out - without this, a connection that went bad while
        # sitting in the pool (network blip, the server killing an idle
        # connection, etc.) gets handed to the next caller anyway, and
        # a write against a truly-dead connection hangs rather than erroring
        # fast, since the client is waiting on a TCP peer that will never
        # respond. Observed in production: after a couple of failed writes,
        # the pool ended up holding a broken connection that made every
        # subsequent write hang until timeout instead of failing immediately.
        # max_size is deliberately small. Supabase's pooler allows a limited
        # number of *client* connections, and gunicorn runs multiple workers
        # that each build their own independent pool - so the number that
        # matters upstream is (workers x max_size), not max_size. At the
        # previous max_size=10 that was 2x10=20, over the budget, and once
        # it was hit the pooler stopped accepting new connections, which
        # surfaces here as "couldn't get a connection" rather than as any
        # kind of explicit limit error. 2x3=6 leaves plenty of headroom, and
        # is still ample for this app's traffic.
        #
        # timeout=10 (default 30) so that if the pool ever does run dry,
        # callers fail fast instead of every request in the app blocking for
        # half a minute first - a 30s wait behind an exhausted pool reads to
        # users as "the whole site is hung", which is worse than an error.
        # THE timeouts below are what actually keep the pool alive, and are
        # not optional tuning. A Postgres socket has no timeout by default:
        # if the peer dies without sending FIN/RST (pooler recycles it, NAT
        # or LB drops the flow, transient partition), the next query on that
        # connection blocks *forever*. That thread is stuck inside the `try`,
        # so the `finally: release_connection()` never runs and the
        # connection is gone from the pool permanently. Repeat max_size times
        # and the pool is dead with no errors logged and no self-recovery -
        # which is exactly what production showed: available=0, size=3,
        # waiting climbing, errors=None, staying that way while fully idle.
        #
        #   connect_timeout - bounds establishing a new connection
        #   keepalives_*    - makes the kernel probe an idle peer and fail
        #                     the socket if it's gone, instead of waiting
        #                     forever for a reply that will never come
        #   statement_timeout - server-side ceiling so a single query can
        #                     never pin a pooled connection indefinitely
        connect_kwargs = {
            'connect_timeout': 10,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 3,
        }

        def _configure(conn):
            # statement_timeout has to be SET here rather than passed as a
            # libpq `options` startup parameter: Supabase's pooler strips
            # that, silently leaving the server default (verified - it stayed
            # at 2min). Applied per new connection by the pool.
            conn.execute("SET statement_timeout = '15s'")
            conn.commit()
        # max_lifetime recycles connections well inside the window where a
        # pooler or LB would silently drop a long-lived one.
        # Deliberately NO check= callback. It was added here to catch stale
        # connections, but ConnectionPool.check_connection works by toggling
        # conn.autocommit, which *raises* on a connection that still has a
        # transaction open ("can't change 'autocommit' now: ... INTRANS" -
        # confirmed directly). psycopg_pool treats every exception from the
        # check as recoverable, so it returns that connection to the pool and
        # retries in a loop; if the same connection keeps failing the check,
        # the loop just spins until the pool timeout and the caller sees
        # "couldn't get a connection" even though connections exist and the
        # database is fine. That matches production exactly: size=3,
        # available=0, errors=0, waiting far above what sync workers could
        # even generate. Staleness is instead handled by the keepalives and
        # max_lifetime/max_idle below - and a stale connection failing one
        # query is much better than every request blocking on a retry loop.
        # Fork-safety. Nothing connects at import time. gunicorn forks its
        # workers *after* importing app.py - and therefore after this
        # module's `db = Database()` has already run - so a pool opened here
        # would hand the very same live SSL socket to every child. Two
        # processes then interleave writes on one TLS stream and the server
        # rejects the garbled records with
        # "SSL error: decryption failed or bad record mac", which is exactly
        # what production returned. Those corrupted connections never come
        # back to the pool, so it bleeds down to empty and every subsequent
        # request fails with PoolTimeout instead - the symptom that masked
        # the real cause for so long.
        #
        # So the pool is built on first use and tagged with the pid that
        # built it. A child that inherited a parent's pool sees the mismatch
        # and builds its own. The inherited object is abandoned rather than
        # closed: closing it would tear down sockets the parent still uses.
        self._connect_kwargs = connect_kwargs
        self._configure_cb = _configure
        self._pool = None
        self._pool_pid = None
        self._pool_lock = threading.Lock()

    def _get_pool(self):
        """Return this process's pool, creating it if this is the first use
        here or if we've been forked since it was created."""
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
                timeout=10, max_lifetime=300, max_idle=60,
            )
            self._pool_pid = pid
            return self._pool

    def get_connection(self):
        """Check a connection out of the pool. Caller must call
        release_connection() when done (finally block), and must call
        conn.commit() explicitly after writes - autocommit is off, matching
        the old sqlite3 default."""
        return self._get_pool().getconn()

    def get_pool_stats(self):
        """Pool counters for /api/health. Exposed because connection-pool
        problems are otherwise invisible from outside the process - they
        surface only as generic timeouts, which is indistinguishable from
        the database itself being slow or unreachable."""
        try:
            pool = self._get_pool()
            # Return psycopg_pool's counters wholesale rather than a curated
            # subset. The hand-picked fields turned out to omit precisely the
            # ones that distinguish the candidate causes: connections_lost
            # (server closed it under us), returns_bad (handed back
            # unusable), connections_errors (couldn't be opened at all) and
            # requests_errors. Debugging this blind has already cost several
            # wrong theories, and the counters are cheap.
            stats = dict(pool.get_stats())
            stats['pid'] = os.getpid()
            stats['max_size_cfg'] = pool.max_size
            return stats
        except Exception as exc:
            return {'error': str(exc)[:100], 'pid': os.getpid()}

    def release_connection(self, conn):
        """Return a connection to the pool. If a write failed partway
        through, roll back first - handing back a connection mid-transaction
        would poison it for whoever borrows it next."""
        try:
            if conn.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
                conn.rollback()
        except Exception:
            # Rollback failed, so this connection can't be cleaned up and
            # must not go back into the pool still dirty - a connection stuck
            # mid-transaction breaks for every subsequent borrower, not just
            # this request. Closing it makes putconn() discard and replace it
            # instead, trading one reconnect for not wedging the pool.
            try:
                conn.close()
            except Exception:
                pass
        self._get_pool().putconn(conn)

    def init_db(self):
        """Verify connectivity. Schema is managed via Supabase migrations,
        not app-startup DDL - a mismatch here should fail loudly at boot
        rather than silently running against tables that don't exist."""
        conn = self.get_connection()
        try:
            conn.execute('SELECT 1 FROM users LIMIT 1')
        finally:
            self.release_connection(conn)

    # USER MANAGEMENT
    def create_user(self, username, email, password):
        """Create new user with hashed password"""
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        return self._insert_user(username, email, password_hash)

    def _insert_user(self, username, email, password_hash):
        """Shared by create_user and OTP-verified signup - takes an
        already-hashed password so the OTP path never has to re-derive or
        re-transmit the plaintext."""
        user_id = hashlib.md5(f"{username}{datetime.now()}".encode()).hexdigest()
        conn = self.get_connection()
        try:
            c = conn.cursor()
            c.execute('''
                INSERT INTO users (id, username, email, password_hash)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, username, email, password_hash))
            conn.commit()
            return user_id
        except psycopg.errors.IntegrityError:
            return None
        finally:
            self.release_connection(conn)

    def get_user(self, username):
        """Get user by username"""
        conn = self.get_connection()
        try:
            c = conn.cursor(row_factory=dict_row)
            c.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = c.fetchone()
            return dict(user) if user else None
        finally:
            self.release_connection(conn)

    def get_user_by_id(self, user_id):
        """Get user by id"""
        conn = self.get_connection()
        try:
            c = conn.cursor(row_factory=dict_row)
            c.execute('SELECT * FROM users WHERE id = %s', (user_id,))
            user = c.fetchone()
            return dict(user) if user else None
        finally:
            self.release_connection(conn)

    def verify_password(self, stored_hash, password):
        """Verify password against stored hash"""
        return bcrypt.checkpw(password.encode(), stored_hash.encode())

    def update_password(self, user_id, new_password):
        """Hash and store a new password for a user"""
        password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        conn = self.get_connection()
        try:
            c = conn.cursor()
            c.execute(
                'UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s',
                (password_hash, user_id),
            )
            conn.commit()
            return c.rowcount > 0
        finally:
            self.release_connection(conn)

    def delete_user(self, user_id):
        """Permanently delete a user and all their data.

        Deleted in explicit dependency order rather than relying on
        cascade, since the foreign keys here don't declare ON DELETE
        CASCADE (matches the original SQLite behaviour, where FKs weren't
        even enforced - here they are enforced, so this order matters more
        than it used to, not less)."""
        conn = self.get_connection()
        try:
            c = conn.cursor()
            c.execute(
                'DELETE FROM messages WHERE conversation_id IN '
                '(SELECT id FROM conversations WHERE user_id = %s)',
                (user_id,),
            )
            c.execute('DELETE FROM conversations WHERE user_id = %s', (user_id,))
            c.execute('DELETE FROM api_usage WHERE user_id = %s', (user_id,))
            c.execute('DELETE FROM personas WHERE user_id = %s', (user_id,))
            c.execute('DELETE FROM password_reset_tokens WHERE user_id = %s', (user_id,))
            c.execute('DELETE FROM users WHERE id = %s', (user_id,))
            conn.commit()
            return c.rowcount > 0
        finally:
            self.release_connection(conn)

    def get_user_by_email(self, email):
        """Get user by email"""
        conn = self.get_connection()
        try:
            c = conn.cursor(row_factory=dict_row)
            c.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = c.fetchone()
            return dict(user) if user else None
        finally:
            self.release_connection(conn)

    # PASSWORD RESET
    def create_password_reset_token(self, user_id, ttl_minutes=60):
        """Generate a single-use reset token, invalidating any earlier
        unused tokens for this user first."""
        conn = self.get_connection()
        try:
            c = conn.cursor()
            c.execute(
                'UPDATE password_reset_tokens SET used = TRUE WHERE user_id = %s AND used = FALSE',
                (user_id,),
            )
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
            c.execute(
                'INSERT INTO password_reset_tokens (token, user_id, expires_at) VALUES (%s, %s, %s)',
                (token, user_id, expires_at),
            )
            conn.commit()
            return token
        finally:
            self.release_connection(conn)

    def get_valid_reset_token(self, token):
        """Return the token row if it exists, is unused, and hasn't expired."""
        conn = self.get_connection()
        try:
            c = conn.cursor(row_factory=dict_row)
            c.execute('SELECT * FROM password_reset_tokens WHERE token = %s', (token,))
            row = c.fetchone()
        finally:
            self.release_connection(conn)
        if not row:
            return None
        row = dict(row)
        if row['used']:
            return None
        if row['expires_at'] < datetime.now(timezone.utc):
            return None
        return row

    def mark_reset_token_used(self, token):
        conn = self.get_connection()
        try:
            conn.execute('UPDATE password_reset_tokens SET used = TRUE WHERE token = %s', (token,))
            conn.commit()
        finally:
            self.release_connection(conn)

    # SIGNUP OTP VERIFICATION
    MAX_OTP_ATTEMPTS = 5

    def create_pending_registration(self, username, email, password, otp_code, ttl_minutes=10):
        """Stage a signup behind an OTP code. Password is hashed immediately -
        this table never holds a plaintext password, even briefly. Replaces
        any earlier pending attempt for the same email (e.g. user hit
        "resend code")."""
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
        conn = self.get_connection()
        try:
            conn.execute(
                '''INSERT INTO pending_registrations
                   (email, username, password_hash, otp_code, attempts, expires_at)
                   VALUES (%s, %s, %s, %s, 0, %s)
                   ON CONFLICT (email) DO UPDATE SET
                       username = excluded.username,
                       password_hash = excluded.password_hash,
                       otp_code = excluded.otp_code,
                       attempts = 0,
                       created_at = NOW(),
                       expires_at = excluded.expires_at''',
                (email, username, password_hash, otp_code, expires_at),
            )
            conn.commit()
        finally:
            self.release_connection(conn)

    def get_pending_registration(self, email):
        """Return the pending row if it exists and hasn't expired (expiry
        alone - attempt-count exhaustion is checked separately by the
        caller so it can distinguish "wrong code" from "too many tries" for
        the user)."""
        conn = self.get_connection()
        try:
            c = conn.cursor(row_factory=dict_row)
            c.execute('SELECT * FROM pending_registrations WHERE email = %s', (email,))
            row = c.fetchone()
        finally:
            self.release_connection(conn)
        if not row:
            return None
        row = dict(row)
        if row['expires_at'] < datetime.now(timezone.utc):
            return None
        return row

    def increment_otp_attempts(self, email):
        """Record a failed verification attempt, returning the new count."""
        conn = self.get_connection()
        try:
            c = conn.cursor(row_factory=dict_row)
            c.execute('UPDATE pending_registrations SET attempts = attempts + 1 WHERE email = %s', (email,))
            conn.commit()
            c.execute('SELECT attempts FROM pending_registrations WHERE email = %s', (email,))
            row = c.fetchone()
            return row['attempts'] if row else self.MAX_OTP_ATTEMPTS
        finally:
            self.release_connection(conn)

    def delete_pending_registration(self, email):
        conn = self.get_connection()
        try:
            conn.execute('DELETE FROM pending_registrations WHERE email = %s', (email,))
            conn.commit()
        finally:
            self.release_connection(conn)

    # CONVERSATION MANAGEMENT
    def create_conversation(self, user_id, title, language='en'):
        """Create new conversation"""
        conv_id = hashlib.md5(f"{user_id}{datetime.now()}".encode()).hexdigest()
        conn = self.get_connection()
        try:
            conn.execute('''
                INSERT INTO conversations (id, user_id, title, language)
                VALUES (%s, %s, %s, %s)
            ''', (conv_id, user_id, title, language))
            conn.commit()
            return conv_id
        finally:
            self.release_connection(conn)

    def get_conversations(self, user_id, limit=50):
        """Get all conversations for user"""
        conn = self.get_connection()
        try:
            c = conn.cursor(row_factory=dict_row)
            c.execute('''
                SELECT * FROM conversations
                WHERE user_id = %s AND is_archived = FALSE
                ORDER BY updated_at DESC
                LIMIT %s
            ''', (user_id, limit))
            return [dict(row) for row in c.fetchall()]
        finally:
            self.release_connection(conn)

    def update_conversation_title(self, conv_id, title):
        """Update conversation title"""
        conn = self.get_connection()
        try:
            conn.execute('''
                UPDATE conversations
                SET title = %s, updated_at = NOW()
                WHERE id = %s
            ''', (title, conv_id))
            conn.commit()
        finally:
            self.release_connection(conn)

    # MESSAGE MANAGEMENT
    def add_message(self, conv_id, sender, text, language='en', tokens=0):
        """Add message to conversation"""
        msg_id = hashlib.md5(f"{conv_id}{datetime.now()}".encode()).hexdigest()
        conn = self.get_connection()
        try:
            c = conn.cursor()
            c.execute('''
                INSERT INTO messages (id, conversation_id, sender, text, language, tokens_used)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (msg_id, conv_id, sender, text, language, tokens))

            # Update conversation timestamp
            c.execute('''
                UPDATE conversations
                SET updated_at = NOW()
                WHERE id = %s
            ''', (conv_id,))

            conn.commit()
            return msg_id
        finally:
            self.release_connection(conn)

    def get_messages(self, conv_id, limit=100):
        """Get messages from conversation"""
        conn = self.get_connection()
        try:
            c = conn.cursor(row_factory=dict_row)
            c.execute('''
                SELECT * FROM messages
                WHERE conversation_id = %s
                ORDER BY timestamp ASC
                LIMIT %s
            ''', (conv_id, limit))
            return [dict(row) for row in c.fetchall()]
        finally:
            self.release_connection(conn)

    def get_conversation_history(self, conv_id, max_tokens=4000):
        """Get conversation history for context"""
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
        """Log API usage for analytics"""
        conn = self.get_connection()
        try:
            conn.execute('''
                INSERT INTO api_usage (user_id, endpoint, tokens_used, cost)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, endpoint, tokens_used, cost))
            conn.commit()
        finally:
            self.release_connection(conn)

    def get_user_stats(self, user_id):
        """Get user statistics"""
        conn = self.get_connection()
        try:
            c = conn.cursor(row_factory=dict_row)

            # Total tokens
            c.execute('''
                SELECT SUM(tokens_used) as total_tokens FROM api_usage
                WHERE user_id = %s
            ''', (user_id,))
            total_tokens = c.fetchone()['total_tokens'] or 0

            # Total conversations
            c.execute('''
                SELECT COUNT(*) as count FROM conversations
                WHERE user_id = %s AND is_archived = FALSE
            ''', (user_id,))
            total_conversations = c.fetchone()['count']

            return {
                'total_tokens': total_tokens,
                'total_conversations': total_conversations
            }
        finally:
            self.release_connection(conn)

    # PERSONA MANAGEMENT
    def create_persona(self, user_id, name, system_prompt):
        """Create a new persona for a user"""
        persona_id = hashlib.md5(f"{user_id}{name}{datetime.now()}".encode()).hexdigest()
        conn = self.get_connection()
        try:
            conn.execute('''
                INSERT INTO personas (id, user_id, name, system_prompt)
                VALUES (%s, %s, %s, %s)
            ''', (persona_id, user_id, name, system_prompt))
            conn.commit()
            return persona_id
        finally:
            self.release_connection(conn)

    def list_personas(self, user_id):
        """List all personas belonging to a user"""
        conn = self.get_connection()
        try:
            c = conn.cursor(row_factory=dict_row)
            c.execute('''
                SELECT * FROM personas WHERE user_id = %s ORDER BY created_at ASC
            ''', (user_id,))
            return [dict(row) for row in c.fetchall()]
        finally:
            self.release_connection(conn)

    def get_persona(self, persona_id, user_id):
        """Get a single persona, scoped to its owner"""
        conn = self.get_connection()
        try:
            c = conn.cursor(row_factory=dict_row)
            c.execute('''
                SELECT * FROM personas WHERE id = %s AND user_id = %s
            ''', (persona_id, user_id))
            persona = c.fetchone()
            return dict(persona) if persona else None
        finally:
            self.release_connection(conn)

    def update_persona(self, persona_id, user_id, name, system_prompt):
        """Update a persona's name/system_prompt. Returns False if it doesn't belong to user_id."""
        if not self.get_persona(persona_id, user_id):
            return False

        conn = self.get_connection()
        try:
            conn.execute('''
                UPDATE personas
                SET name = %s, system_prompt = %s, updated_at = NOW()
                WHERE id = %s AND user_id = %s
            ''', (name, system_prompt, persona_id, user_id))
            conn.commit()
            return True
        finally:
            self.release_connection(conn)

    def delete_persona(self, persona_id, user_id):
        """Delete a persona. Returns False if it doesn't belong to user_id."""
        if not self.get_persona(persona_id, user_id):
            return False

        conn = self.get_connection()
        try:
            conn.execute('DELETE FROM personas WHERE id = %s AND user_id = %s', (persona_id, user_id))
            conn.commit()
            return True
        finally:
            self.release_connection(conn)

# Global instance
db = Database()
