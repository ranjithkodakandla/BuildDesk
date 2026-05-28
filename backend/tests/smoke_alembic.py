"""
Smoke Tests: Alembic Schema Migration
=====================================
Validates that the database schema can be safely upgraded and downgraded
using Alembic migrations.
"""

import subprocess
import sqlite3
import sys

# Test configuration
DB_PATH = "builddesk.db"
PASS = "✓"
FAIL = "✗"

def section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")

def ok(label: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"  {PASS}  [{label}]{suffix}")

def fail(label: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"  {FAIL}  [{label}]{suffix}")
    sys.exit(1)

def run_cmd(cmd: str) -> bool:
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr)
        return False
    return True

def get_tables() -> list:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    conn.close()
    return tables

def run_all() -> None:
    print("\nBuildDesk · Alembic Migration Smoke Tests")

    # ── 1. Downgrade to Base ─────────────────────────────────────────────────
    section("1. Downgrade to Base")
    if not run_cmd("alembic downgrade base"):
        fail("downgrade", "Failed to downgrade to base")
    
    tables = get_tables()
    expected_tables = ["alembic_version"]
    # SQLite might have sqlite_sequence but our tables shouldn't be there
    domain_tables = [t for t in tables if t in ["tenants", "projects", "geometries"]]
    if domain_tables:
        fail("downgrade", f"Tables {domain_tables} still exist after downgrade to base")
    ok("alembic downgrade", "Successfully dropped all domain tables")

    # ── 2. Upgrade to Head ───────────────────────────────────────────────────
    section("2. Upgrade to Head")
    if not run_cmd("alembic upgrade head"):
        fail("upgrade", "Failed to upgrade to head")
    
    tables = get_tables()
    for t in ["tenants", "projects", "geometries"]:
        if t not in tables:
            fail("upgrade", f"Expected table '{t}' not found after upgrade")
    ok("alembic upgrade", "Successfully applied migrations and created tables")

    print(f"\n{'═' * 60}")
    print(f"  All Alembic migration smoke tests passed.")
    print(f"{'═' * 60}\n")

if __name__ == "__main__":
    run_all()
