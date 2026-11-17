"""Use map coordinates for mission routes.

Revision ID: 0005_mission_map_coordinates
Revises: 0004_optional_character_grade
Create Date: 2026-11-17
"""
from alembic import op
import sqlalchemy as sa


revision = "0005_mission_map_coordinates"
down_revision = "0004_optional_character_grade"
branch_labels = None
depends_on = None


def _noms_anciennes_cles_etrangeres():
    contraintes = sa.inspect(op.get_bind()).get_foreign_keys("missions")
    noms = {}
    for contrainte in contraintes:
        colonnes = contrainte.get("constrained_columns") or []
        if colonnes == ["secteur_depart_id"]:
            noms["secteur_depart_id"] = contrainte.get("name")
        elif colonnes == ["secteur_arrivee_id"]:
            noms["secteur_arrivee_id"] = contrainte.get("name")
    return noms


def upgrade():
    connexion = op.get_bind()
    carte_id = connexion.execute(
        sa.text("SELECT id FROM cartes WHERE code = :code"),
        {"code": "terres_neutres"},
    ).scalar_one_or_none()
    if carte_id is None:
        raise RuntimeError(
            "Migration impossible : la carte de code 'terres_neutres' "
            "est absente de la table cartes."
        )

    op.add_column(
        "missions",
        sa.Column("carte_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "missions",
        sa.Column("depart_x", sa.Integer(), nullable=True),
    )
    op.add_column(
        "missions",
        sa.Column("depart_y", sa.Integer(), nullable=True),
    )
    op.add_column(
        "missions",
        sa.Column("arrivee_x", sa.Integer(), nullable=True),
    )
    op.add_column(
        "missions",
        sa.Column("arrivee_y", sa.Integer(), nullable=True),
    )
    connexion.execute(
        sa.text("UPDATE missions SET carte_id = :carte_id"),
        {"carte_id": carte_id},
    )

    anciennes_cles = _noms_anciennes_cles_etrangeres()
    with op.batch_alter_table("missions") as batch_op:
        batch_op.alter_column(
            "carte_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        for colonne in ("secteur_depart_id", "secteur_arrivee_id"):
            nom = anciennes_cles.get(colonne)
            if nom is not None:
                batch_op.drop_constraint(nom, type_="foreignkey")
            batch_op.drop_column(colonne)
        batch_op.create_foreign_key(
            "fk_missions_carte_id_cartes",
            "cartes",
            ["carte_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    op.create_index(
        "ix_missions_carte_id",
        "missions",
        ["carte_id"],
        unique=False,
    )


def downgrade():
    coordonnees_utilisees = op.get_bind().execute(
        sa.text(
            "SELECT COUNT(*) FROM missions WHERE "
            "depart_x IS NOT NULL OR depart_y IS NOT NULL OR "
            "arrivee_x IS NOT NULL OR arrivee_y IS NOT NULL"
        )
    ).scalar_one()
    if coordonnees_utilisees:
        raise RuntimeError(
            "Impossible de supprimer les coordonnées cartographiques : "
            "des missions en possèdent déjà."
        )

    op.drop_index("ix_missions_carte_id", table_name="missions")
    contraintes = sa.inspect(op.get_bind()).get_foreign_keys("missions")
    carte_fk = next(
        (
            contrainte.get("name")
            for contrainte in contraintes
            if (contrainte.get("constrained_columns") or []) == ["carte_id"]
        ),
        None,
    )

    with op.batch_alter_table("missions") as batch_op:
        if carte_fk is not None:
            batch_op.drop_constraint(carte_fk, type_="foreignkey")
        batch_op.add_column(
            sa.Column("secteur_depart_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("secteur_arrivee_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_missions_secteur_depart_id_secteurs",
            "secteurs",
            ["secteur_depart_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_foreign_key(
            "fk_missions_secteur_arrivee_id_secteurs",
            "secteurs",
            ["secteur_arrivee_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.drop_column("carte_id")
        batch_op.drop_column("depart_x")
        batch_op.drop_column("depart_y")
        batch_op.drop_column("arrivee_x")
        batch_op.drop_column("arrivee_y")
