"""initial schema (users, missions, places, rankings, votes, agents, incidents)

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000

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


def upgrade() -> None:
    # ----- Extensions -----
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ----- users -----
    op.execute(
        """
        CREATE TABLE users (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            email           citext UNIQUE NOT NULL,
            password_hash   text NOT NULL,
            display_name    text NOT NULL,
            avatar_url      text,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            deleted_at      timestamptz
        )
        """
    )
    op.create_index("users_email_idx", "users", ["email"])

    # ----- missions -----
    # Note: places(id) is created below; we add the FKs (winner_place_id,
    # backup_place_id) AFTER the `places` table exists.
    op.execute(
        """
        CREATE TABLE missions (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            creator_id      uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            title           text NOT NULL,
            description     text,
            status          text NOT NULL CHECK (status IN
                            ('draft','collecting','ranking','voting','decided','cancelled')),
            location_lat    double precision NOT NULL,
            location_lng    double precision NOT NULL,
            search_radius_m integer NOT NULL DEFAULT 3000,
            scheduled_for   timestamptz,
            winner_place_id uuid,
            backup_place_id uuid,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.create_index("missions_creator_idx", "missions", ["creator_id"])
    op.create_index("missions_status_idx", "missions", ["status"])

    # ----- mission_members -----
    op.execute(
        """
        CREATE TABLE mission_members (
            mission_id      uuid NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
            user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role            text NOT NULL CHECK (role IN ('owner','member')),
            joined_at       timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (mission_id, user_id)
        )
        """
    )

    # ----- mission_invites -----
    op.execute(
        """
        CREATE TABLE mission_invites (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            mission_id      uuid NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
            token           text UNIQUE NOT NULL,
            expires_at      timestamptz NOT NULL,
            max_uses        integer NOT NULL DEFAULT 10,
            uses            integer NOT NULL DEFAULT 0,
            created_at      timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.create_index("mission_invites_mission_idx", "mission_invites", ["mission_id"])

    # ----- preferences -----
    op.execute(
        """
        CREATE TABLE preferences (
            mission_id              uuid NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
            user_id                 uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            budget_max_cents        integer,
            distance_tolerance_m    integer,
            cuisines_like           text[] NOT NULL DEFAULT '{}',
            cuisines_dislike        text[] NOT NULL DEFAULT '{}',
            dietary_restrictions    text[] NOT NULL DEFAULT '{}',
            vibe                    text,
            noise_tolerance         smallint CHECK (noise_tolerance BETWEEN 0 AND 5),
            seating_preference      text,
            urgency                 smallint CHECK (urgency BETWEEN 0 AND 5),
            hunger_level            smallint CHECK (hunger_level BETWEEN 0 AND 5),
            raw_comment             text,
            parsed_at               timestamptz,
            updated_at              timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (mission_id, user_id)
        )
        """
    )

    # ----- places -----
    op.execute(
        """
        CREATE TABLE places (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            google_place_id text UNIQUE NOT NULL,
            name            text NOT NULL,
            address         text,
            lat             double precision NOT NULL,
            lng             double precision NOT NULL,
            price_level     smallint CHECK (price_level BETWEEN 0 AND 4),
            rating          numeric(2,1),
            user_rating_ct  integer,
            cuisines        text[] NOT NULL DEFAULT '{}',
            raw_blob        jsonb NOT NULL,
            vibe_embedding  vector(1536),
            fetched_at      timestamptz NOT NULL DEFAULT now(),
            expires_at      timestamptz NOT NULL,
            created_at      timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.create_index("places_google_id_idx", "places", ["google_place_id"])
    op.create_index("places_expires_idx", "places", ["expires_at"])
    op.execute(
        "CREATE INDEX places_vibe_ivfflat_idx ON places "
        "USING ivfflat (vibe_embedding vector_cosine_ops)"
    )

    # Now wire missions -> places FKs.
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
    op.execute(
        """
        CREATE TABLE agent_runs (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            mission_id      uuid NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
            graph_name      text NOT NULL,
            status          text NOT NULL CHECK (status IN
                            ('running','succeeded','failed','interrupted','cancelled')),
            trigger         text NOT NULL,
            input           jsonb NOT NULL,
            output          jsonb,
            error           text,
            started_at      timestamptz NOT NULL DEFAULT now(),
            finished_at     timestamptz,
            total_tokens    integer,
            total_cost_usd  numeric(10,6)
        )
        """
    )
    op.create_index(
        "agent_runs_mission_idx",
        "agent_runs",
        ["mission_id", sa.text("started_at DESC")],
    )
    op.create_index("agent_runs_status_idx", "agent_runs", ["status"])

    # ----- rankings -----
    op.execute(
        """
        CREATE TABLE rankings (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            mission_id      uuid NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
            place_id        uuid NOT NULL REFERENCES places(id),
            agent_run_id    uuid NOT NULL REFERENCES agent_runs(id),
            rank            integer NOT NULL,
            score           numeric(5,2) NOT NULL,
            reasons         jsonb NOT NULL,
            created_at      timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.create_index("rankings_mission_run_idx", "rankings", ["mission_id", "agent_run_id"])

    # ----- votes -----
    op.execute(
        """
        CREATE TABLE votes (
            mission_id      uuid NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
            user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            place_id        uuid NOT NULL REFERENCES places(id),
            weight          smallint NOT NULL DEFAULT 1,
            created_at      timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (mission_id, user_id, place_id)
        )
        """
    )

    # ----- agent_run_steps -----
    op.execute(
        """
        CREATE TABLE agent_run_steps (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_run_id    uuid NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
            node_name       text NOT NULL,
            status          text NOT NULL,
            input           jsonb,
            output          jsonb,
            tool_calls      jsonb,
            error           text,
            latency_ms      integer,
            started_at      timestamptz NOT NULL,
            finished_at     timestamptz
        )
        """
    )
    op.create_index(
        "agent_run_steps_run_idx",
        "agent_run_steps",
        ["agent_run_id", "started_at"],
    )

    # ----- incidents -----
    op.execute(
        """
        CREATE TABLE incidents (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            kind            text NOT NULL,
            severity        text NOT NULL CHECK (severity IN ('info','warn','error','critical')),
            status          text NOT NULL CHECK (status IN ('open','acknowledged','resolved')),
            title           text NOT NULL,
            details         jsonb NOT NULL,
            related_run_id  uuid REFERENCES agent_runs(id),
            opened_at       timestamptz NOT NULL DEFAULT now(),
            resolved_at     timestamptz
        )
        """
    )
    op.create_index(
        "incidents_status_idx",
        "incidents",
        ["status", sa.text("opened_at DESC")],
    )


def downgrade() -> None:
    # Drop in reverse dependency order.
    op.drop_index("incidents_status_idx", table_name="incidents")
    op.execute("DROP TABLE IF EXISTS incidents")

    op.drop_index("agent_run_steps_run_idx", table_name="agent_run_steps")
    op.execute("DROP TABLE IF EXISTS agent_run_steps")

    op.execute("DROP TABLE IF EXISTS votes")

    op.drop_index("rankings_mission_run_idx", table_name="rankings")
    op.execute("DROP TABLE IF EXISTS rankings")

    op.drop_index("agent_runs_status_idx", table_name="agent_runs")
    op.drop_index("agent_runs_mission_idx", table_name="agent_runs")
    op.execute("DROP TABLE IF EXISTS agent_runs")

    op.drop_constraint("missions_backup_place_id_fkey", "missions", type_="foreignkey")
    op.drop_constraint("missions_winner_place_id_fkey", "missions", type_="foreignkey")

    op.execute("DROP INDEX IF EXISTS places_vibe_ivfflat_idx")
    op.drop_index("places_expires_idx", table_name="places")
    op.drop_index("places_google_id_idx", table_name="places")
    op.execute("DROP TABLE IF EXISTS places")

    op.execute("DROP TABLE IF EXISTS preferences")

    op.drop_index("mission_invites_mission_idx", table_name="mission_invites")
    op.execute("DROP TABLE IF EXISTS mission_invites")

    op.execute("DROP TABLE IF EXISTS mission_members")

    op.drop_index("missions_status_idx", table_name="missions")
    op.drop_index("missions_creator_idx", table_name="missions")
    op.execute("DROP TABLE IF EXISTS missions")

    op.drop_index("users_email_idx", table_name="users")
    op.execute("DROP TABLE IF EXISTS users")

    # Leave extensions in place — other schemas (langgraph) may use them.


# Silence "imported but unused" for postgresql alias (kept for future use in autogen).
_ = postgresql
