"""SQLite migration runner."""

from pathlib import Path

from core.database import utc_now


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def ensure_migration_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version TEXT PRIMARY KEY,
          applied_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def applied_versions(conn):
    ensure_migration_table(conn)
    rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version").fetchall()
    return {row["version"] for row in rows}


def migration_files():
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted(path for path in MIGRATIONS_DIR.glob("*.sql") if path.is_file())


def run_migrations(conn):
    ensure_migration_table(conn)
    applied = applied_versions(conn)
    for path in migration_files():
        version = path.stem
        if version in applied:
            continue
        sql = path.read_text(encoding="utf-8")
        with conn:
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (version, utc_now()),
            )


def migration_status(conn):
    applied = applied_versions(conn)
    status = []
    for path in migration_files():
        status.append({
            "version": path.stem,
            "path": str(path),
            "applied": path.stem in applied,
        })
    return status
