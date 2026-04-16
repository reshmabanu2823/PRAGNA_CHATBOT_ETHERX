"""
Gunicorn configuration for production deployment.

Usage:
    gunicorn -c gunicorn_config.py wsgi:app
"""

import multiprocessing
import os

# ===========================
# Server Configuration
# ===========================
bind = os.getenv('GUNICORN_BIND', '0.0.0.0:5001')
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
threads = int(os.getenv('GUNICORN_THREADS', 2))
worker_class = os.getenv('GUNICORN_WORKER_CLASS', 'gthread')

# ===========================
# Timeout Configuration
# ===========================
timeout = int(os.getenv('GUNICORN_TIMEOUT', 120))
keepalive = int(os.getenv('GUNICORN_KEEPALIVE', 5))

# ===========================
# Logging Configuration
# ===========================
loglevel = os.getenv('GUNICORN_LOGLEVEL', 'info')
accesslog = os.getenv('GUNICORN_ACCESSLOG', '-')
errorlog = os.getenv('GUNICORN_ERRORLOG', '-')
logfile = os.getenv('GUNICORN_LOGFILE', None)

# ===========================
# Process Configuration
# ===========================
max_requests = int(os.getenv('GUNICORN_MAX_REQUESTS', 1000))
max_requests_jitter = int(os.getenv('GUNICORN_MAX_REQUESTS_JITTER', 100))

# ===========================
# TLS Configuration (Optional)
# ===========================
# Uncomment to enable HTTPS:
# keyfile = os.getenv('GUNICORN_KEYFILE', None)
# certfile = os.getenv('GUNICORN_CERTFILE', None)
# ssl_version = 'TLSv1_2'

# ===========================
# Application Configuration
# ===========================
application_close_timeout = int(os.getenv('GUNICORN_APP_CLOSE_TIMEOUT', 30))

# ===========================
# Pre-fork Server Hook
# ===========================
def on_starting(server):
    """Hook run before the master process is initialized."""
    print('[Gunicorn] Server is starting...')

def when_ready(server):
    """Hook run when the server is ready to accept connections."""
    print(f'[Gunicorn] Server ready. Spawning {workers} workers with {threads} threads each')
    print(f'[Gunicorn] Listening on {bind}')
    print(f'[Gunicorn] Worker timeout: {timeout}s')

def on_exit(server):
    """Hook run when the master process receives a TERM or INT signal."""
    print('[Gunicorn] Server shutting down...')

# ===========================
# Print Configuration on Startup
# ===========================
print(f"""
╔════════════════════════════════════════════════════════╗
║          GUNICORN PRODUCTION CONFIGURATION             ║
╠════════════════════════════════════════════════════════╣
║ Bind: {bind:<45} ║
║ Workers: {workers:<40} ║
║ Threads/Worker: {threads:<35} ║
║ Worker Timeout: {timeout}s{' ' * (35 - len(str(timeout)))} ║
║ Log Level: {loglevel:<40} ║
║ Max Requests: {max_requests:<38} ║
╚════════════════════════════════════════════════════════╝
""")
