"""Add maps and their painted cells.

Revision ID: 0003_map_tables
Revises: 0002_core_business_tables
Create Date: 2026-11-13
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_map_tables"
down_revision = "0002_core_business_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cartes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("largeur", sa.Integer(), nullable=False),
        sa.Column("hauteur", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "largeur > 0 AND hauteur > 0",
            name="ck_cartes_dimensions_positives",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "cases_carte",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("carte_id", sa.Integer(), nullable=False),
        sa.Column("x", sa.Integer(), nullable=False),
        sa.Column("y", sa.Integer(), nullable=False),
        sa.Column("terrain_code", sa.String(length=40), nullable=False),
        sa.Column("variant", sa.Integer(), nullable=False),
        sa.CheckConstraint("x >= 0", name="ck_cases_carte_x_non_negatif"),
        sa.CheckConstraint("y >= 0", name="ck_cases_carte_y_non_negatif"),
        sa.CheckConstraint(
            "variant BETWEEN 1 AND 4",
            name="ck_cases_carte_variant",
        ),
        sa.ForeignKeyConstraint(
            ["carte_id"],
            ["cartes.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "carte_id",
            "x",
            "y",
            name="uq_cases_carte_carte_id_x_y",
        ),
    )

    cartes = sa.table(
        "cartes",
        sa.column("code", sa.String()),
        sa.column("nom", sa.String()),
        sa.column("largeur", sa.Integer()),
        sa.column("hauteur", sa.Integer()),
    )
    op.bulk_insert(
        cartes,
        [
            {
                "code": "terres_neutres",
                "nom": "Terres Neutres",
                "largeur": 100,
                "hauteur": 100,
            },
            {
                "code": "paradis",
                "nom": "Paradis",
                "largeur": 100,
                "hauteur": 100,
            },
            {
                "code": "enfer",
                "nom": "Enfer",
                "largeur": 100,
                "hauteur": 100,
            },
            {
                "code": "limbes",
                "nom": "Limbes",
                "largeur": 100,
                "hauteur": 100,
            },
        ],
    )


def downgrade():
    op.drop_table("cases_carte")
    op.drop_table("cartes")
