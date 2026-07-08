import os

HOST = "0.0.0.0"
PORT = 8080
EXTERNAL_PORT = 80  # iptables redirects :80 → :PORT

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
PITSTOP_DATA_DIR = "/data/pitstop"
BACKUP_DIR_NAME = "backups"
