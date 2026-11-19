"""Use the mission assignment statuses requested by the application.

Revision ID: 0006_affectation_statuses
Revises: 0005_mission_map_coordinates
Create Date: 2026-11-19
"""
from alembic import op
import sqlalchemy as sa


revision = "0006_affectation_statuses"
down_revision = "0005_mission_map_coordinates"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("affectations") as batch_op:
        batch_op.drop_constraint(
            "ck_affectations_statut",
            type_="check",
        )
    op.execute(
        sa.text(
            "UPDATE affectations SET statut = CASE "
            "WHEN statut IN ('proposee', 'acceptee') THEN 'en_cours' "
            "WHEN statut = 'validee' THEN 'terminee' "
            "WHEN statut IN ('refusee', 'annulee') THEN 'revoquee' "
            "ELSE statut END"
        )
    )
    with op.batch_alter_table("affectations") as batch_op:
        batch_op.create_check_constraint(
            "ck_affectations_statut",
            "statut IN ('en_cours', 'terminee', 'revoquee')",
        )
        batch_op.alter_column(
            "statut",
            existing_type=sa.String(length=20),
            server_default="en_cours",
        )


def downgrade():
    with op.batch_alter_table("affectations") as batch_op:
        batch_op.drop_constraint(
            "ck_affectations_statut",
            type_="check",
        )
    op.execute(
        sa.text(
            "UPDATE affectations SET statut = CASE "
            "WHEN statut = 'terminee' THEN 'validee' "
            "WHEN statut = 'revoquee' THEN 'annulee' "
            "WHEN statut = 'en_cours' THEN 'acceptee' "
            "ELSE statut END"
        )
    )
    with op.batch_alter_table("affectations") as batch_op:
        batch_op.create_check_constraint(
            "ck_affectations_statut",
            "statut IN ('proposee', 'acceptee', 'en_cours', 'validee', 'refusee', 'annulee')",
        )
        batch_op.alter_column(
            "statut",
            existing_type=sa.String(length=20),
            server_default="proposee",
        )
