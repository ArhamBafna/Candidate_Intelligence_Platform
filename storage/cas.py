import hashlib
import os
import stat
from pathlib import Path

class CASManager:
    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir)
        
    def store(self, content: bytes, extension: str = "") -> tuple[str, str]:
        """
        Store content in the CAS file structure.
        Returns (sha256_hash, absolute_file_path).
        """
        if extension and not extension.startswith('.'):
            extension = f".{extension}"
            
        file_hash = hashlib.sha256(content).hexdigest()
        
        # Path sharding: /ab/cd/abcdef...ext
        shard1 = file_hash[:2]
        shard2 = file_hash[2:4]
        filename = f"{file_hash}{extension}"
        
        target_dir = self.root_dir / shard1 / shard2
        target_dir.mkdir(parents=True, exist_ok=True)
        
        target_path = target_dir / filename
        
        if not target_path.exists():
            target_path.write_bytes(content)
            # Make the file read-only (0444)
            target_path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

        return file_hash, str(target_path.absolute())

    def delete(self, file_path: str | Path) -> bool:
        """
        Remove one stored object (issue #14).

        store() marks files read-only; the read-only attribute must be cleared
        before unlinking (required on Windows). Best-effort: returns False on
        failure instead of raising, so callers can degrade to a warning.
        """
        path = Path(file_path)
        try:
            if not path.exists():
                return True
            path.chmod(stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            path.unlink()
            return True
        except OSError:
            return False
