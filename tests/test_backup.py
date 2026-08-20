import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def tmp_db(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO test (name) VALUES ('hello')")
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def backup_env(tmp_path, monkeypatch):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("services.backup.DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr("services.backup.DOCS_DIR", tmp_path)
    return backup_dir


class TestBackupDatabase:
    def test_creates_backup_file(self, tmp_db, backup_env):
        from services.backup import backup_database
        db_path = str(tmp_db.parent / "test.db")
        result = backup_database(backup_path=str(backup_env / "test_backup.db"))
        assert Path(result).exists()

    def test_backup_is_valid_sqlite(self, tmp_db, backup_env):
        from services.backup import backup_database
        dest = str(backup_env / "valid.db")
        backup_database(backup_path=dest)
        conn = sqlite3.connect(dest)
        rows = conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
        conn.close()
        assert rows[0] > 0


class TestRestoreDatabase:
    def test_restore_valid_backup(self, tmp_db, backup_env):
        from services.backup import backup_database, restore_database
        dest = str(backup_env / "restore_test.db")
        backup_database(backup_path=dest)
        result = restore_database(dest)
        assert result is True

    def test_restore_invalid_file(self, backup_env):
        from services.backup import restore_database
        bad = backup_env / "bad.txt"
        bad.write_text("not a db")
        with pytest.raises(ValueError, match="invalide"):
            restore_database(str(bad))

    def test_restore_missing_file(self):
        from services.backup import restore_database
        with pytest.raises(FileNotFoundError):
            restore_database("/nonexistent/path/backup.db")


class TestDeleteBackup:
    def test_delete_existing(self, backup_env):
        from services.backup import delete_backup
        f = backup_env / "delete_me.db"
        f.touch()
        result = delete_backup(str(f))
        assert result is True
        assert not f.exists()

    def test_delete_nonexistent(self):
        from services.backup import delete_backup
        result = delete_backup("/nonexistent/backup.db")
        assert result is False
