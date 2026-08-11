import sqlite3
import os
import shutil
import hashlib
import json
from pathlib import Path

class BackupManager:
    """
    Handles live backups of the SQLite database and syncing the CAS storage.
    """

    def perform_live_backup(self, source_db_path: str, backup_db_path: str) -> None:
        """
        Executes a live hot backup using sqlite3.backup API.
        """
        # Ensure backup directory exists
        Path(backup_db_path).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(source_db_path) as source_conn:
            with sqlite3.connect(backup_db_path) as backup_conn:
                source_conn.backup(backup_conn, pages=100, sleep=0.01)

    def sync_cas_storage(self, source_cas_dir: str, backup_cas_dir: str) -> None:
        """
        Copies any new files from the source CAS directory to the backup CAS directory.
        Since CAS files are immutable, they are never modified after creation.
        """
        source_path = Path(source_cas_dir)
        backup_path = Path(backup_cas_dir)

        if not source_path.exists():
            return

        for root, _, files in os.walk(source_cas_dir):
            for file in files:
                src_file = Path(root) / file
                rel_path = src_file.relative_to(source_path)
                dest_file = backup_path / rel_path

                if not dest_file.exists():
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dest_file)

    def _get_lance_row_count(self, vector_dir: str) -> int:
        """
        Attempts to read row count from LanceDB. Returns 0 if missing.
        """
        try:
            import lancedb
            if not Path(vector_dir).exists():
                return 0
            db = lancedb.connect(vector_dir)
            if "candidate_sections" in db.table_names():
                tbl = db.open_table("candidate_sections")
                return len(tbl)
            return 0
        except Exception:
            return 0

    def generate_manifest(self, db_path: str, cas_dir: str, vector_dir: str) -> dict:
        """
        Generates a JSON manifest containing SHA256 of the backup DB, CAS file count, and vector count.
        """
        manifest = {
            "db_sha256": None,
            "cas_file_count": 0,
            "vector_count": self._get_lance_row_count(vector_dir)
        }

        # Calculate DB hash
        db_file = Path(db_path)
        if db_file.exists():
            hasher = hashlib.sha256()
            with open(db_file, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            manifest["db_sha256"] = hasher.hexdigest()

        # Count CAS files
        cas_path = Path(cas_dir)
        if cas_path.exists():
            count = sum(1 for _ in cas_path.rglob('*') if _.is_file())
            manifest["cas_file_count"] = count

        return manifest
