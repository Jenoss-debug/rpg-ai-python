"""Add the first MR business tables.

Revision ID: 0002_core_business_tables
Revises: 0001_initial_schema
Create Date: 2026-11-12
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_core_business_tables"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "grades",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("rang", sa.Integer(), nullable=False),
        sa.CheckConstraint("rang BETWEEN 1 AND 5", name="ck_grades_rang"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("nom"),
        sa.UniqueConstraint("rang", name="uq_grades_rang"),
    )

    op.create_table(
        "secteurs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nom"),
    )

    op.create_table(
        "types_missions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column(
            "actif",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("nom"),
    )

    grades = sa.table(
        "grades",
        sa.column("code", sa.String()),
        sa.column("nom", sa.String()),
        sa.column("rang", sa.Integer()),
    )
    op.bulk_insert(
        grades,
        [
            {"code": "prince_des_lettres", "nom": "Prince des lettres", "rang": 1},
            {"code": "grand_intendant_des_routes", "nom": "Grand intendant des routes", "rang": 2},
            {"code": "maitre_des_relais", "nom": "Maître des relais", "rang": 3},
            {"code": "messager", "nom": "Messager", "rang": 4},
            {"code": "apprenti_messager", "nom": "Apprenti messager", "rang": 5},
        ],
    )

    types_missions = sa.table(
        "types_missions",
        sa.column("code", sa.String()),
        sa.column("nom", sa.String()),
        sa.column("actif", sa.Boolean()),
    )
    op.bulk_insert(
        types_missions,
        [
            {"code": "livraison", "nom": "Livraison", "actif": True},
            {"code": "recrutement", "nom": "Recrutement", "actif": True},
            {"code": "gestion_secteur", "nom": "Gestion de secteur", "actif": True},
            {"code": "securite", "nom": "Sécurité", "actif": True},
            {"code": "escorte", "nom": "Escorte", "actif": True},
        ],
    )

    op.create_table(
        "personnages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("matricule", sa.String(length=50), nullable=False),
        sa.Column("nom", sa.String(length=100), nullable=False),
        sa.Column("utilisateur_id", sa.Integer(), nullable=False),
        sa.Column("grade_id", sa.Integer(), nullable=False),
        sa.Column("cree_par_utilisateur_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["cree_par_utilisateur_id"],
            ["utilisateurs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["grade_id"],
            ["grades.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["utilisateur_id"],
            ["utilisateurs.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("matricule"),
    )
    op.create_index(
        "ix_personnages_grade_id", "personnages", ["grade_id"], unique=False
    )
    op.create_index(
        "ix_personnages_utilisateur_id", "personnages", ["utilisateur_id"], unique=False
    )

    op.create_table(
        "missions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("titre", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("description_publique", sa.Text(), nullable=True),
        sa.Column(
            "publique",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("type_mission_id", sa.Integer(), nullable=False),
        sa.Column("secteur_id", sa.Integer(), nullable=True),
        sa.Column("secteur_depart_id", sa.Integer(), nullable=True),
        sa.Column("secteur_arrivee_id", sa.Integer(), nullable=True),
        sa.Column("recompense_po", sa.Integer(), nullable=True),
        sa.Column(
            "statut",
            sa.String(length=20),
            server_default="brouillon",
            nullable=False,
        ),
        sa.Column("cree_par_utilisateur_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "recompense_po IS NULL OR recompense_po >= 0",
            name="ck_missions_recompense",
        ),
        sa.CheckConstraint(
            "statut IN ('brouillon', 'ouverte', 'en_cours', 'terminee', 'annulee')",
            name="ck_missions_statut",
        ),
        sa.ForeignKeyConstraint(
            ["cree_par_utilisateur_id"],
            ["utilisateurs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["secteur_arrivee_id"],
            ["secteurs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["secteur_depart_id"],
            ["secteurs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["secteur_id"],
            ["secteurs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["type_mission_id"],
            ["types_missions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_missions_secteur_id", "missions", ["secteur_id"], unique=False
    )
    op.create_index(
        "ix_missions_statut", "missions", ["statut"], unique=False
    )
    op.create_index(
        "ix_missions_type_mission_id", "missions", ["type_mission_id"], unique=False
    )

    op.create_table(
        "mission_grades",
        sa.Column("mission_id", sa.Integer(), nullable=False),
        sa.Column("grade_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["grade_id"], ["grades.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["mission_id"], ["missions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("mission_id", "grade_id"),
    )

    op.create_table(
        "affectations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mission_id", sa.Integer(), nullable=False),
        sa.Column("personnage_id", sa.Integer(), nullable=False),
        sa.Column("recrue_personnage_id", sa.Integer(), nullable=True),
        sa.Column("nb_livraisons_formation_validees", sa.Integer(), nullable=True),
        sa.Column("prime_po", sa.Integer(), nullable=True),
        sa.Column("prime_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "statut",
            sa.String(length=20),
            server_default="proposee",
            nullable=False,
        ),
        sa.Column("validee_par_utilisateur_id", sa.Integer(), nullable=True),
        sa.Column("validee_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "nb_livraisons_formation_validees IS NULL OR "
            "nb_livraisons_formation_validees BETWEEN 0 AND 3",
            name="ck_affectations_livraisons_formation",
        ),
        sa.CheckConstraint(
            "prime_po IS NULL OR prime_po >= 0",
            name="ck_affectations_prime",
        ),
        sa.CheckConstraint(
            "statut IN ('proposee', 'acceptee', 'en_cours', 'validee', 'refusee', 'annulee')",
            name="ck_affectations_statut",
        ),
        sa.ForeignKeyConstraint(
            ["mission_id"], ["missions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["personnage_id"], ["personnages.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["recrue_personnage_id"], ["personnages.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["validee_par_utilisateur_id"],
            ["utilisateurs.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "mission_id",
            "personnage_id",
            name="uq_affectations_mission_personnage",
        ),
    )
    op.create_index(
        "ix_affectations_personnage_id",
        "affectations",
        ["personnage_id"],
        unique=False,
    )
    op.create_index(
        "ix_affectations_recrue_personnage_id",
        "affectations",
        ["recrue_personnage_id"],
        unique=False,
    )
    op.create_index(
        "ix_affectations_statut", "affectations", ["statut"], unique=False
    )


def downgrade():
    op.drop_index("ix_affectations_statut", table_name="affectations")
    op.drop_index("ix_affectations_recrue_personnage_id", table_name="affectations")
    op.drop_index("ix_affectations_personnage_id", table_name="affectations")
    op.drop_table("affectations")

    op.drop_table("mission_grades")
    op.drop_index("ix_missions_type_mission_id", table_name="missions")
    op.drop_index("ix_missions_statut", table_name="missions")
    op.drop_index("ix_missions_secteur_id", table_name="missions")
    op.drop_table("missions")

    op.drop_index("ix_personnages_utilisateur_id", table_name="personnages")
    op.drop_index("ix_personnages_grade_id", table_name="personnages")
    op.drop_table("personnages")

    op.drop_table("types_missions")
    op.drop_table("secteurs")
    op.drop_table("grades")
