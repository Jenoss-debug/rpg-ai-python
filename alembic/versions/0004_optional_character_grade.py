"""Allow characters without a grade.

Revision ID: 0004_optional_character_grade
Revises: 0003_map_tables
Create Date: 2026-11-15
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_optional_character_grade"
down_revision = "0003_map_tables"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("personnages") as batch_op:
        batch_op.alter_column(
            "grade_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade():
    connexion = op.get_bind()
    personnages_sans_grade = connexion.execute(
        sa.text("SELECT COUNT(*) FROM personnages WHERE grade_id IS NULL")
    ).scalar_one()
    if personnages_sans_grade:
        raise RuntimeError(
            "Impossible de rendre personnages.grade_id obligatoire : "
            "des personnages n’ont aucun grade."
        )

    with op.batch_alter_table("personnages") as batch_op:
        batch_op.alter_column(
            "grade_id",
            existing_type=sa.Integer(),
            existing_nullable=True,
            nullable=False,
        )
