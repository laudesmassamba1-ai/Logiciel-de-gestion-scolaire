#!/usr/bin/env bash
# Demarre le serveur de l'ecole PUIS l'application en mode synchronise.
#
# Prerequis (une seule fois) :
#   1. sudo mysql < scripts/init_mysql.sql     (base + utilisateur)
#   2. Modifier GS_DB_PASSWORD ci-dessous si vous avez change le mot de passe.
#
# Arret : fermez l'application, le serveur s'arrete automatiquement.

set -e
cd "$(dirname "$0")/.."

export GS_DB_HOST="${GS_DB_HOST:-localhost}"
export GS_DB_USER="${GS_DB_USER:-gs_app}"
export GS_DB_PASSWORD="${GS_DB_PASSWORD:-gs_motdepasse_a_changer}"
export GS_DB_NAME="${GS_DB_NAME:-ecole}"
export GS_API_URL="${GS_API_URL:-http://127.0.0.1:8000}"
export GS_SYNC_ACTIVE=true

echo "[1/2] Serveur GS sur $GS_API_URL (base MySQL '$GS_DB_NAME')..."
.venv/bin/python -m uvicorn server.main:app --host 127.0.0.1 --port 8000 &
SERVEUR=$!
trap 'kill $SERVEUR 2>/dev/null || true' EXIT

sleep 3
echo "[2/2] Application en mode En Ligne..."
.venv/bin/python main.py
