#!/usr/bin/env python3
"""Apply the Challenge 02 status-code compatibility patch once, with guards."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
changes = {
    "app/models.py": [
        (
            "from sqlalchemy import DateTime, String, UniqueConstraint, JSON",
            "from sqlalchemy import DateTime, String, UniqueConstraint, JSON, SmallInteger",
        ),
        (
            '    status: Mapped[str] = mapped_column(String(30), nullable=False, default="confirmed")',
            '    status: Mapped[str] = mapped_column(String(30), nullable=False, default="confirmed")\n'
            '    # Nullable while old application versions coexist with this expanded schema.\n'
            '    status_code: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)',
        ),
    ],
    "app/main.py": [
        (
            '            request_hash=digest,\n            status="confirmed",\n',
            '            request_hash=digest,\n            status="confirmed",\n            status_code=2,  # confirmed; see the versioned status-code mapping migration\n',
        ),
    ],
    "tests/test_orders_integration.py": [
        (
            '                status VARCHAR(30) NOT NULL,\n                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),',
            '                status VARCHAR(30) NOT NULL,\n                status_code SMALLINT NULL,\n                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),',
        ),
    ],
    "migrations/env.py": [
        (
            "from logging.config import fileConfig\n",
            "from logging.config import fileConfig\nimport os\n",
        ),
        (
            "config = context.config\n",
            'config = context.config\n\n'
            '# Allow isolated CI/local migration tests to override alembic.ini safely.\n'
            'database_url = os.environ.get("DATABASE_URL")\n'
            'if database_url:\n'
            '    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))\n',
        ),
    ],
}

prepared = {}
errors = []
for rel, pairs in changes.items():
    path = ROOT / rel
    if not path.exists():
        errors.append(f"Missing required file: {rel}")
        continue
    source = path.read_text()
    updated = source
    for old, new in pairs:
        if new in updated:
            continue
        count = updated.count(old)
        if count != 1:
            errors.append(f"{rel}: expected one occurrence of patch target, found {count}: {old[:90]!r}")
            break
        updated = updated.replace(old, new, 1)
    prepared[rel] = updated

if errors:
    print("No files were modified because validation failed:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    sys.exit(1)

for rel, content in prepared.items():
    (ROOT / rel).write_text(content)

print("PASS: Challenge 02 application/schema compatibility patch applied.")
for rel in prepared:
    print(f"  updated {rel}")
print("Next, run the shell/YAML checks; do not run a migration against your existing database yet.")
