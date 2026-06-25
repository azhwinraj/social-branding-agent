"""post type columns and draft revision history

Revision ID: c9f8a2b1d3e7
Revises: 787f72f5cc42
Create Date: 2026-06-25

Uses PRAGMA table_info checks before every ADD COLUMN so the migration is
idempotent — safe to re-run if Base.metadata.create_all() already applied
part of the schema.

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9f8a2b1d3e7"
down_revision: Union[str, Sequence[str], None] = "787f72f5cc42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn: sa.engine.Connection, table: str, column: str) -> bool:
    rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return any(row[1] == column for row in rows)


def _has_index(conn: sa.engine.Connection, index: str) -> bool:
    row = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='index' AND name=:n"),
        {"n": index},
    ).fetchone()
    return row is not None


def _table_exists(conn: sa.engine.Connection, table: str) -> bool:
    row = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"),
        {"n": table},
    ).fetchone()
    return row is not None


def upgrade() -> None:
    conn = op.get_bind()

    # --- drafts: three new columns ---
    if not _has_column(conn, "drafts", "post_types_json"):
        conn.execute(sa.text("ALTER TABLE drafts ADD COLUMN post_types_json TEXT"))
    if not _has_column(conn, "drafts", "post_type"):
        conn.execute(sa.text("ALTER TABLE drafts ADD COLUMN post_type VARCHAR(64)"))
    if not _has_column(conn, "drafts", "model_tier"):
        conn.execute(sa.text("ALTER TABLE drafts ADD COLUMN model_tier INTEGER"))

    # --- style_examples: post_type + compound index for type-filtered retrieval ---
    if not _has_column(conn, "style_examples", "post_type"):
        conn.execute(sa.text("ALTER TABLE style_examples ADD COLUMN post_type VARCHAR(64)"))
    if not _has_index(conn, "idx_style_examples_platform_type"):
        conn.execute(sa.text(
            "CREATE INDEX idx_style_examples_platform_type"
            " ON style_examples(platform, post_type)"
        ))

    # --- draft_revisions table ---
    if not _table_exists(conn, "draft_revisions"):
        conn.execute(sa.text("""
            CREATE TABLE draft_revisions (
                id                     VARCHAR(64)  NOT NULL,
                draft_id               INTEGER      NOT NULL
                                           REFERENCES drafts(id) ON DELETE CASCADE,
                revision_number        INTEGER      NOT NULL,
                content                TEXT         NOT NULL,
                refinement_instruction TEXT,
                model_used             VARCHAR(128) NOT NULL,
                tier                   INTEGER      NOT NULL,
                tokens_in              INTEGER,
                tokens_out             INTEGER,
                cost_usd               FLOAT,
                latency_ms             INTEGER,
                adherence_passed       BOOLEAN,
                adherence_failures     TEXT,
                is_current             BOOLEAN      NOT NULL,
                created_at             DATETIME     NOT NULL,
                PRIMARY KEY (id),
                UNIQUE (draft_id, revision_number)
            )
        """))

    if not _has_index(conn, "idx_revisions_current"):
        conn.execute(sa.text(
            "CREATE INDEX idx_revisions_current"
            " ON draft_revisions(draft_id, is_current)"
        ))

    # --- backfill: seed revision 0 for any draft that doesn't have one yet ---
    rows = conn.execute(
        sa.text("SELECT id, content, created_at FROM drafts")
    ).fetchall()
    for row in rows:
        draft_id, content, created_at = row[0], row[1], row[2]
        already_exists = conn.execute(
            sa.text(
                "SELECT 1 FROM draft_revisions"
                " WHERE draft_id = :did AND revision_number = 0"
            ),
            {"did": draft_id},
        ).fetchone()
        if not already_exists:
            conn.execute(
                sa.text(
                    "INSERT INTO draft_revisions"
                    " (id, draft_id, revision_number, content,"
                    "  refinement_instruction, model_used, tier,"
                    "  is_current, created_at)"
                    " VALUES (:id, :did, 0, :content, NULL, 'unknown', 1, 1, :ts)"
                ),
                {"id": f"r0-{draft_id}", "did": draft_id, "content": content, "ts": created_at},
            )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_index(conn, "idx_revisions_current"):
        conn.execute(sa.text("DROP INDEX idx_revisions_current"))
    if _table_exists(conn, "draft_revisions"):
        conn.execute(sa.text("DROP TABLE draft_revisions"))
    if _has_index(conn, "idx_style_examples_platform_type"):
        conn.execute(sa.text("DROP INDEX idx_style_examples_platform_type"))
    # Added columns are left in place on downgrade — SQLite makes column removal
    # expensive and the data is harmless.
