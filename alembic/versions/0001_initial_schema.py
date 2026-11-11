"""Baseline for the existing users and deliveries schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-11
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "utilisateurs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('admin', 'coursier')",
            name="ck_utilisateurs_role",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )

    op.create_table(
        "livraisons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(length=30), nullable=False),
        sa.Column("nom_client", sa.String(length=100), nullable=True),
        sa.Column("destinataire", sa.String(length=100), nullable=False),
        sa.Column("secteur_depart", sa.String(length=100), nullable=False),
        sa.Column("secteur_arrivee", sa.String(length=100), nullable=False),
        sa.Column("coord_depart_x", sa.Integer(), nullable=True),
        sa.Column("coord_depart_y", sa.Integer(), nullable=True),
        sa.Column("coord_arrivee_x", sa.Integer(), nullable=True),
        sa.Column("coord_arrivee_y", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("recompense_po", sa.Integer(), nullable=False),
        sa.Column("statut", sa.String(length=20), nullable=False),
        sa.Column("coursier_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "recompense_po >= 0",
            name="ck_livraisons_recompense",
        ),
        sa.CheckConstraint(
            "statut IN ('a_preparer', 'en_cours', 'livree')",
            name="ck_livraisons_statut",
        ),
        sa.ForeignKeyConstraint(
            ["coursier_id"],
            ["utilisateurs.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference"),
    )
    op.create_index(
        "ix_livraisons_coursier_id",
        "livraisons",
        ["coursier_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_livraisons_coursier_id", table_name="livraisons")
    op.drop_table("livraisons")
    op.drop_table("utilisateurs")
