"""initial schema (users, missions, places, rankings, votes, agents, incidents)

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000

Dual-dialect: works on both Postgres (with pgvector) and SQLite. The migration
branches on ``op.get_context().dialect.name`` for Postgres-only features
(extensions, pgvector column type, ivfflat index). Everywhere else we lean on
SQLAlchemy's portable types so the same DDL emits sensible SQL on either side.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    return op.get_context().dialect.name == "postgresql"


def upgrade() -> None:
    is_pg = _is_postgres()

    # ----- Extensions (Postgres only) -----
    if is_pg:
        op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Choose the embedding column type per dialect.
    if is_pg:
        # Local import so SQLite environments don't need pgvector installed
        # at migration time (it's still in deps, but this keeps the module
        # importable cleanly in either world).
        from pgvector.sqlalchemy import Vector  # type: ignore[import-not-found]

        embedding_col_type: sa.types.TypeEngine = Vector(1536)
    else:
        embedding_col_type = sa.JSON()

    # ----- users -----
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="users_email_key"),
    )
    op.create_index("users_email_idx", "users", ["email"])

    # ----- missions -----
    # NB: places(id) is created below; the FKs (winner_place_id, backup_place_id)
    # are added AFTER the `places` table exists.
    op.create_table(
        "missions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "creator_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("location_lat", sa.Float(), nullable=False),
        sa.Column("location_lng", sa.Float(), nullable=False),
        sa.Column(
            "search_radius_m",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("3000"),
        ),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("winner_place_id", sa.String(36), nullable=True),
        sa.Column("backup_place_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft','collecting','ranking','voting','decided','cancelled')",
            name="missions_status_check",
        ),
    )
    op.create_index("missions_creator_idx", "missions", ["creator_id"])
    op.create_index("missions_status_idx", "missions", ["status"])

    # ----- mission_members -----
    op.create_table(
        "mission_members",
        sa.Column(
            "mission_id",
            sa.String(36),
            sa.ForeignKey("missions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "role IN ('owner','member')", name="mission_members_role_check"
        ),
    )

    # ----- mission_invites -----
    op.create_table(
        "mission_invites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "mission_id",
            sa.String(36),
            sa.ForeignKey("missions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "max_uses", sa.Integer(), nullable=False, server_default=sa.text("10")
        ),
        sa.Column("uses", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("token", name="mission_invites_token_key"),
    )
    op.create_index("mission_invites_mission_idx", "mission_invites", ["mission_id"])

    # ----- preferences -----
    op.create_table(
        "preferences",
        sa.Column(
            "mission_id",
            sa.String(36),
            sa.ForeignKey("missions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("budget_max_cents", sa.Integer(), nullable=True),
        sa.Column("distance_tolerance_m", sa.Integer(), nullable=True),
        sa.Column("cuisines_like", sa.JSON(), nullable=False),
        sa.Column("cuisines_dislike", sa.JSON(), nullable=False),
        sa.Column("dietary_restrictions", sa.JSON(), nullable=False),
        sa.Column("vibe", sa.Text(), nullable=True),
        sa.Column("noise_tolerance", sa.SmallInteger(), nullable=True),
        sa.Column("seating_preference", sa.Text(), nullable=True),
        sa.Column("urgency", sa.SmallInteger(), nullable=True),
        sa.Column("hunger_level", sa.SmallInteger(), nullable=True),
        sa.Column("raw_comment", sa.Text(), nullable=True),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "noise_tolerance BETWEEN 0 AND 5",
            name="preferences_noise_tolerance_check",
        ),
        sa.CheckConstraint(
            "urgency BETWEEN 0 AND 5", name="preferences_urgency_check"
        ),
        sa.CheckConstraint(
            "hunger_level BETWEEN 0 AND 5", name="preferences_hunger_level_check"
        ),
    )

    # ----- places -----
    op.create_table(
        "places",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("google_place_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("price_level", sa.SmallInteger(), nullable=True),
        sa.Column("rating", sa.Numeric(2, 1), nullable=True),
        sa.Column("user_rating_ct", sa.Integer(), nullable=True),
        sa.Column("cuisines", sa.JSON(), nullable=False),
        sa.Column("raw_blob", sa.JSON(), nullable=False),
        sa.Column("vibe_embedding", embedding_col_type, nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "price_level BETWEEN 0 AND 4", name="places_price_level_check"
        ),
        sa.UniqueConstraint("google_place_id", name="places_google_place_id_key"),
    )
    op.create_index("places_google_id_idx", "places", ["google_place_id"])
    op.create_index("places_expires_idx", "places", ["expires_at"])
    if is_pg:
        # ivfflat index — Postgres + pgvector only.
        op.execute(
            "CREATE INDEX places_vibe_ivfflat_idx ON places "
            "USING ivfflat (vibe_embedding vector_cosine_ops)"
        )

    # Now wire missions -> places FKs.
    # SQLite cannot ALTER a table to add a foreign key after creation, so we
    # only emit these on Postgres. The corresponding ORM-level FK declarations
    # still apply for cascade/relationship semantics.
    if is_pg:
        op.create_foreign_key(
            "missions_winner_place_id_fkey",
            "missions",
            "places",
            ["winner_place_id"],
            ["id"],
        )
        op.create_foreign_key(
            "missions_backup_place_id_fkey",
            "missions",
            "places",
            ["backup_place_id"],
            ["id"],
        )

    # ----- agent_runs (must exist before rankings, which references it) -----
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "mission_id",
            sa.String(36),
            sa.ForeignKey("missions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("graph_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("trigger", sa.Text(), nullable=False),
        sa.Column("input", sa.JSON(), nullable=False),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("total_cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.CheckConstraint(
            "status IN ('running','succeeded','failed','interrupted','cancelled')",
            name="agent_runs_status_check",
        ),
    )
    op.create_index(
        "agent_runs_mission_idx",
        "agent_runs",
        ["mission_id", sa.text("started_at DESC")],
    )
    op.create_index("agent_runs_status_idx", "agent_runs", ["status"])

    # ----- rankings -----
    op.create_table(
        "rankings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "mission_id",
            sa.String(36),
            sa.ForeignKey("missions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "place_id",
            sa.String(36),
            sa.ForeignKey("places.id"),
            nullable=False,
        ),
        sa.Column(
            "agent_run_id",
            sa.String(36),
            sa.ForeignKey("agent_runs.id"),
            nullable=False,
        ),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "rankings_mission_run_idx", "rankings", ["mission_id", "agent_run_id"]
    )

    # ----- votes -----
    op.create_table(
        "votes",
        sa.Column(
            "mission_id",
            sa.String(36),
            sa.ForeignKey("missions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "place_id",
            sa.String(36),
            sa.ForeignKey("places.id"),
            primary_key=True,
        ),
        sa.Column(
            "weight", sa.SmallInteger(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ----- agent_run_steps -----
    op.create_table(
        "agent_run_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "agent_run_id",
            sa.String(36),
            sa.ForeignKey("agent_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("node_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("input", sa.JSON(), nullable=True),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column("tool_calls", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "agent_run_steps_run_idx",
        "agent_run_steps",
        ["agent_run_id", "started_at"],
    )

    # ----- incidents -----
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column(
            "related_run_id",
            sa.String(36),
            sa.ForeignKey("agent_runs.id"),
            nullable=True,
        ),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "severity IN ('info','warn','error','critical')",
            name="incidents_severity_check",
        ),
        sa.CheckConstraint(
            "status IN ('open','acknowledged','resolved')",
            name="incidents_status_check",
        ),
    )
    op.create_index(
        "incidents_status_idx",
        "incidents",
        ["status", sa.text("opened_at DESC")],
    )


def downgrade() -> None:
    is_pg = _is_postgres()

    # Drop in reverse dependency order.
    op.drop_index("incidents_status_idx", table_name="incidents")
    op.drop_table("incidents")

    op.drop_index("agent_run_steps_run_idx", table_name="agent_run_steps")
    op.drop_table("agent_run_steps")

    op.drop_table("votes")

    op.drop_index("rankings_mission_run_idx", table_name="rankings")
    op.drop_table("rankings")

    op.drop_index("agent_runs_status_idx", table_name="agent_runs")
    op.drop_index("agent_runs_mission_idx", table_name="agent_runs")
    op.drop_table("agent_runs")

    if is_pg:
        op.drop_constraint(
            "missions_backup_place_id_fkey", "missions", type_="foreignkey"
        )
        op.drop_constraint(
            "missions_winner_place_id_fkey", "missions", type_="foreignkey"
        )
        op.execute("DROP INDEX IF EXISTS places_vibe_ivfflat_idx")

    op.drop_index("places_expires_idx", table_name="places")
    op.drop_index("places_google_id_idx", table_name="places")
    op.drop_table("places")

    op.drop_table("preferences")

    op.drop_index("mission_invites_mission_idx", table_name="mission_invites")
    op.drop_table("mission_invites")

    op.drop_table("mission_members")

    op.drop_index("missions_status_idx", table_name="missions")
    op.drop_index("missions_creator_idx", table_name="missions")
    op.drop_table("missions")

    op.drop_index("users_email_idx", table_name="users")
    op.drop_table("users")

    # Leave extensions in place — other schemas (langgraph) may use them.


# Silence "imported but unused" for postgresql alias (kept for future use in autogen).
_ = postgresql
