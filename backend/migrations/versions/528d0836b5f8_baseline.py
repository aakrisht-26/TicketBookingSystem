"""Baseline.

Creates no schema. Step 2 owns every table, index and view in
``docs/DATA-MODEL.md``, and this revision deliberately anticipates none of it.

What it does create, by being applied at all, is ``alembic_version``: the row
that tells every later revision where the database currently stands. It is the
root of the chain, so it is also what makes ``downgrade base`` mean something,
and CI runs upgrade, downgrade and upgrade again on every pull request to prove
the pipeline works before there is any schema for a broken one to damage.

Revision ID: 528d0836b5f8
Revises:
Create Date: 2026-08-22 20:59:05.981080
"""

revision: str = "528d0836b5f8"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """No schema. See the module docstring."""


def downgrade() -> None:
    """No schema. See the module docstring."""
