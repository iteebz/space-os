from datetime import datetime
from pathlib import Path
import sqlite3

from space.os.core.storage import Repo
from space.os.db.migration import apply_migrations
from space.os.lib import uuid7
from space.apps.spawn.models import Identity, Constitution
import hashlib

class SpawnRepo(Repo):
    SCHEMA_FILES = [
        "V1__initial_spawn_schema.py",
    ]

    def __init__(self, app_name: str, db_path: Path | None = None):
        super().__init__(app_name, db_path=db_path)

    def create_table(self):
        with self._connect() as conn:
            apply_migrations(self._app_root_path, conn)

    def get_constitution_by_hash(self, constitution_hash: str) -> Constitution | None:
        with self._connect(row_factory=sqlite3.Row) as conn:
            cursor = conn.execute("SELECT id, name, version, content, identity_id, previous_version_id, created_at, created_by, change_description, hash FROM constitutions WHERE hash = ?", (constitution_hash,))
            row = cursor.fetchone()
            if row:
                return Constitution(**row)
            return None

    def add_constitution(self, name: str, version: str, content: str, identity_id: str | None = None, previous_version_id: str | None = None, created_by: str | None = None, change_description: str | None = None) -> Constitution:
        constitution_hash = hashlib.sha256(content.encode()).hexdigest()
        created_at = int(datetime.now().timestamp())

        # Check if constitution with this hash already exists
        existing_constitution = self.get_constitution_by_hash(constitution_hash)
        if existing_constitution:
            return existing_constitution

        self._execute(
            "INSERT INTO constitutions (id, name, version, content, identity_id, previous_version_id, created_at, created_by, change_description, hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid7.uuid7()), name, version, content, identity_id, previous_version_id, created_at, created_by, change_description, constitution_hash)
        )
        return self.get_constitution_by_hash(constitution_hash)

    def add_identity(self, id: str, type: str, initial_constitution_hash: str | None = None) -> Identity:
        created_at = int(datetime.now().timestamp())
        updated_at = created_at
        current_constitution_id = None

        if initial_constitution_hash:
            constitution = self.get_constitution_by_hash(initial_constitution_hash)
            if constitution:
                current_constitution_id = constitution.id
            else:
                raise ValueError(f"Constitution with hash '{initial_constitution_hash}' not found.")

        self._execute(
            "INSERT INTO identities (id, type, current_constitution_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (id, type, current_constitution_id, created_at, updated_at)
        )
        return self.get_identity(id)

    def get_identity(self, id: str) -> Identity | None:
        with self._connect(row_factory=sqlite3.Row) as conn:
            cursor = conn.execute("SELECT id, type, current_constitution_id, created_at, updated_at FROM identities WHERE id = ?", (id,))
            row = cursor.fetchone()
            if row:
                return Identity(**row)
            return None

    def get_constitution_version(self, constitution_id: str) -> Constitution | None:
        with self._connect(row_factory=sqlite3.Row) as conn:
            cursor = conn.execute("SELECT id, name, version, content, identity_id, previous_version_id, created_at, created_by, change_description FROM constitutions WHERE id = ?", (constitution_id,))
            row = cursor.fetchone()
            if row:
                return Constitution(**row)
            return None
