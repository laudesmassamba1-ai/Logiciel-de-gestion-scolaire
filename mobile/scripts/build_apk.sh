#!/usr/bin/env bash
# Prépare la source du build APK puis lance buildozer.
# Le dossier build_src contient le backend partagé (core, database, models,
# repositories, services) + l'application Kivy (mobile/). Il est régénéré à
# chaque build pour rester synchronisé avec le dépôt.
set -euo pipefail

MOBILE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT_DIR="$(cd "$MOBILE_DIR/.." && pwd)"
STAGING="$MOBILE_DIR/build_src"

if [ -x "$ROOT_DIR/.venv/bin/buildozer" ]; then
  BUILDENV="$ROOT_DIR/.venv/bin"
  export PATH="$BUILDENV:$PATH"
  export VIRTUAL_ENV="$ROOT_DIR/.venv"
fi

rm -rf "$STAGING"
mkdir -p "$STAGING"

for pkg in core database models repositories services; do
  if [ -d "$ROOT_DIR/$pkg" ]; then
    cp -r "$ROOT_DIR/$pkg" "$STAGING/$pkg"
  fi
done

cp -r "$MOBILE_DIR/app" "$STAGING/app"
cp "$MOBILE_DIR/main.py" "$STAGING/main.py"

find "$STAGING" -name "__pycache__" -type d -prune -exec rm -rf {} \;

cd "$MOBILE_DIR"
exec buildozer android "${1:-debug}"
