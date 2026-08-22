"""${message}

Say what this revision changes and why, not what the SQL says. Justify every
index here: `docs/DATA-MODEL.md` requires an index to explain which query it
serves, so that a later reader can tell a load-bearing index from a hopeful one.

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}
revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | None = ${repr(branch_labels)}
depends_on: str | None = ${repr(depends_on)}


def upgrade() -> None:
    """Apply this revision."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Undo this revision.

    Every revision needs one that works. CI runs upgrade, downgrade and upgrade
    again on each pull request, so a one-way migration is caught here rather
    than the first time it needs reverting.
    """
    ${downgrades if downgrades else "pass"}
