"""Alembic wiring.

No migration exists yet and none is applied here. What is asserted is that the
environment resolves its connection URL from application settings and that no
connection string is committed.
"""

import os
import subprocess
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.settings import Settings

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BACKEND_ROOT / "alembic.ini"
VERSIONS = BACKEND_ROOT / "migrations" / "versions"


def test_no_connection_string_is_committed() -> None:
    """A secret in a committed file is a step failure, per docs/STANDARDS.md."""
    ini = ALEMBIC_INI.read_text(encoding="utf-8")
    active = [
        line for line in ini.splitlines() if line.strip() and not line.lstrip().startswith("#")
    ]

    assert not any(line.startswith("sqlalchemy.url") for line in active)


def test_there_is_exactly_one_head() -> None:
    """Two heads mean two people branched the schema and neither noticed.

    Alembic will refuse to upgrade, but only at deploy time. This fails in the
    pull request instead.
    """
    script = ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))

    assert len(script.get_heads()) == 1


def test_the_baseline_is_the_root_of_the_chain() -> None:
    """`downgrade base` has to have somewhere to land."""
    script = ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))
    roots = [revision for revision in script.walk_revisions() if revision.down_revision is None]

    assert len(roots) == 1
    assert roots[0].doc.startswith("Baseline")


def test_the_baseline_creates_no_schema() -> None:
    """Step 2 owns every table. A baseline that anticipates it is a scope leak."""
    baseline = next(VERSIONS.glob("*_baseline.py")).read_text(encoding="utf-8")

    for ddl in ("op.create_table", "op.create_index", "op.execute", "op.add_column"):
        assert ddl not in baseline


def test_offline_mode_resolves_the_url_from_settings(settings: Settings) -> None:
    """Offline mode runs env.py end to end without opening a connection.

    It is the only way to prove the URL wiring before a database exists. The
    emitted SQL is empty because there are no revisions; what matters is that
    env.py ran, read Settings, and did not fall back to alembic.ini.
    """
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={
            **os.environ,
            "DATABASE_URL": settings.database_url,
            "ENVIRONMENT": settings.environment.value,
        },
    )

    assert result.returncode == 0, result.stderr


def test_alembic_will_not_run_without_the_settings_url() -> None:
    """The complement of the test above.

    Together they prove the URL comes from Settings: with it Alembic runs, and
    without it Alembic fails on Settings validation rather than quietly falling
    back to a value in alembic.ini.
    """
    environment = {key: value for key, value in os.environ.items() if key != "DATABASE_URL"}

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )

    assert result.returncode != 0
    assert "database_url" in result.stderr.lower()
