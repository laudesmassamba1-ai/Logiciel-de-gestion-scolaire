import datetime
import os
import shutil
import sqlite3
from pathlib import Path

from core.config import DB_PATH, DOCS_DIR


def backup_database(backup_path: str = None) -> str:
    if not backup_path:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = DOCS_DIR / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = str(backup_dir / f"ecole_backup_{timestamp}.db")
    src = Path(DB_PATH)
    if not src.exists():
        raise FileNotFoundError(f"Base de donnees introuvable : {DB_PATH}")
    shutil.copy2(str(src), backup_path)
    return backup_path


def restore_database(backup_path: str) -> bool:
    src = Path(backup_path)
    if not src.exists():
        raise FileNotFoundError(f"Fichier de sauvegarde introuvable : {backup_path}")
    conn = sqlite3.connect(str(src))
    try:
        conn.execute("SELECT COUNT(*) FROM sqlite_master")
    except Exception as e:
        conn.close()
        raise ValueError(f"Fichier de sauvegarde invalide : {e}")
    finally:
        conn.close()
    dest = Path(DB_PATH)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dest))
    return True


def list_backups() -> list:
    backup_dir = DOCS_DIR / "backups"
    if not backup_dir.exists():
        return []
    backups = []
    for f in sorted(backup_dir.glob("ecole_backup_*.db"), reverse=True):
        stat = f.stat()
        backups.append({
            "path": str(f),
            "name": f.name,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "date": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M:%S"),
        })
    return backups


def delete_backup(backup_path: str) -> bool:
    p = Path(backup_path).resolve()
    backup_dir = (DOCS_DIR / "backups").resolve()
    if p.exists() and str(p).startswith(str(backup_dir) + os.sep):
        p.unlink()
        return True
    return False
