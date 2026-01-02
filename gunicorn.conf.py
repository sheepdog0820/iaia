"""
Gunicorn設定ファイル
"""
import multiprocessing
import os

# サーバーソケット
bind = "127.0.0.1:8000"
backlog = 2048

# ワーカープロセス
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# スレッド
threads = 2

# デーモン化
daemon = False
raw_env = [
    'DJANGO_SETTINGS_MODULE=tableno.settings_production',
]

# ロギング
accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# プロセス名
proc_name = 'tableno'

# サーバーメカニクス
preload_app = True
reload = False

# SSL設定（必要な場合）
# keyfile = "path/to/keyfile"
# certfile = "path/to/certfile"