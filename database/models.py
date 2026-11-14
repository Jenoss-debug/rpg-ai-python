
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Carte(Base):
    __tablename__ = "cartes"

    __table_args__ = (
        CheckConstraint(
            "largeur > 0 AND hauteur > 0",
            name="ck_cartes_dimensions_positives"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    largeur: Mapped[int] = mapped_column(Integer, nullable=False)
    hauteur: Mapped[int] = mapped_column(Integer, nullable=False)

    cases: Mapped[list[CaseCarte]] = relationship(
        back_populates="carte",
        cascade="all, delete-orphan",
        passive_deletes=True
    )


class CaseCarte(Base):
    __tablename__ = "cases_carte"

    __table_args__ = (
        UniqueConstraint(
            "carte_id",
            "x",
            "y",
            name="uq_cases_carte_carte_id_x_y"
        ),
        CheckConstraint("x >= 0", name="ck_cases_carte_x_non_negatif"),
        CheckConstraint("y >= 0", name="ck_cases_carte_y_non_negatif"),
        CheckConstraint(
            "variant BETWEEN 1 AND 4",
            name="ck_cases_carte_variant"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    carte_id: Mapped[int] = mapped_column(
        ForeignKey("cartes.id", ondelete="CASCADE"),
        nullable=False
    )
    x: Mapped[int] = mapped_column(Integer, nullable=False)
    y: Mapped[int] = mapped_column(Integer, nullable=False)
    terrain_code: Mapped[str] = mapped_column(String(40), nullable=False)
    variant: Mapped[int] = mapped_column(Integer, nullable=False)

    carte: Mapped[Carte] = relationship(back_populates="cases")


class Utilisateur(Base):

    __tablename__ = "utilisateurs"

    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'coursier')",
            name="ck_utilisateurs_role"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="coursier"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    personnages: Mapped[list[Personnage]] = relationship(
        back_populates="compte",
        foreign_keys="Personnage.utilisateur_id"
    )
    personnages_crees: Mapped[list[Personnage]] = relationship(
        back_populates="createur",
        foreign_keys="Personnage.cree_par_utilisateur_id"
    )



class Livraison(Base):
    __tablename__ = "livraisons"

    __table_args__ = (
        CheckConstraint(
            "statut IN ('a_preparer', 'en_cours', 'livree')",
            name="ck_livraisons_statut"
        ),
        CheckConstraint(
            "recompense_po >= 0",
            name="ck_livraisons_recompense"
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    reference: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        nullable=False
    )

    nom_client: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    destinataire: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    secteur_depart: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    secteur_arrivee: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    coord_depart_x: Mapped[int | None] = mapped_column(Integer)
    coord_depart_y: Mapped[int | None] = mapped_column(Integer)

    coord_arrivee_x: Mapped[int | None] = mapped_column(Integer)
    coord_arrivee_y: Mapped[int | None] = mapped_column(Integer)

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    recompense_po: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    statut: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="a_preparer"
    )

    coursier_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )


class Grade(Base):
    __tablename__ = "grades"

    __table_args__ = (
        CheckConstraint("rang BETWEEN 1 AND 5", name="ck_grades_rang"),
        UniqueConstraint("rang", name="uq_grades_rang"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    rang: Mapped[int] = mapped_column(Integer, nullable=False)

    personnages: Mapped[list[Personnage]] = relationship(
        back_populates="grade"
    )
    missions_autorisees: Mapped[list[Mission]] = relationship(
        secondary="mission_grades",
        back_populates="grades_autorises"
    )


class Secteur(Base):
    __tablename__ = "secteurs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    missions: Mapped[list[Mission]] = relationship(
        back_populates="secteur",
        foreign_keys="Mission.secteur_id"
    )
    missions_depart: Mapped[list[Mission]] = relationship(
        back_populates="secteur_depart",
        foreign_keys="Mission.secteur_depart_id"
    )
    missions_arrivee: Mapped[list[Mission]] = relationship(
        back_populates="secteur_arrivee",
        foreign_keys="Mission.secteur_arrivee_id"
    )


class TypeMission(Base):
    __tablename__ = "types_missions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    actif: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true"
    )

    missions: Mapped[list[Mission]] = relationship(back_populates="type_mission")


mission_grades = Table(
    "mission_grades",
    Base.metadata,
    Column(
        "mission_id",
        ForeignKey("missions.id", ondelete="CASCADE"),
        primary_key=True
    ),
    Column(
        "grade_id",
        ForeignKey("grades.id", ondelete="RESTRICT"),
        primary_key=True
    ),
)


class Personnage(Base):
    __tablename__ = "personnages"

    __table_args__ = (
        Index("ix_personnages_utilisateur_id", "utilisateur_id"),
        Index("ix_personnages_grade_id", "grade_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    matricule: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    utilisateur_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="RESTRICT"),
        nullable=False
    )
    grade_id: Mapped[int] = mapped_column(
        ForeignKey("grades.id", ondelete="RESTRICT"),
        nullable=False
    )
    cree_par_utilisateur_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="RESTRICT"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    compte: Mapped[Utilisateur] = relationship(
        back_populates="personnages",
        foreign_keys=[utilisateur_id]
    )
    createur: Mapped[Utilisateur] = relationship(
        back_populates="personnages_crees",
        foreign_keys=[cree_par_utilisateur_id]
    )
    grade: Mapped[Grade] = relationship(back_populates="personnages")
    affectations: Mapped[list[Affectation]] = relationship(
        back_populates="personnage",
        foreign_keys="Affectation.personnage_id"
    )
    affectations_comme_recrue: Mapped[list[Affectation]] = relationship(
        back_populates="recrue",
        foreign_keys="Affectation.recrue_personnage_id"
    )


class Mission(Base):
    __tablename__ = "missions"

    __table_args__ = (
        CheckConstraint(
            "statut IN ('brouillon', 'ouverte', 'en_cours', 'terminee', 'annulee')",
            name="ck_missions_statut"
        ),
        CheckConstraint(
            "recompense_po IS NULL OR recompense_po >= 0",
            name="ck_missions_recompense"
        ),
        Index("ix_missions_type_mission_id", "type_mission_id"),
        Index("ix_missions_secteur_id", "secteur_id"),
        Index("ix_missions_statut", "statut"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titre: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    description_publique: Mapped[str | None] = mapped_column(Text, nullable=True)
    publique: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false"
    )
    type_mission_id: Mapped[int] = mapped_column(
        ForeignKey("types_missions.id", ondelete="RESTRICT"),
        nullable=False
    )
    secteur_id: Mapped[int | None] = mapped_column(
        ForeignKey("secteurs.id", ondelete="RESTRICT"),
        nullable=True
    )
    secteur_depart_id: Mapped[int | None] = mapped_column(
        ForeignKey("secteurs.id", ondelete="RESTRICT"),
        nullable=True
    )
    secteur_arrivee_id: Mapped[int | None] = mapped_column(
        ForeignKey("secteurs.id", ondelete="RESTRICT"),
        nullable=True
    )
    recompense_po: Mapped[int | None] = mapped_column(Integer, nullable=True)
    statut: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="brouillon",
        server_default="brouillon"
    )
    cree_par_utilisateur_id: Mapped[int] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="RESTRICT"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    type_mission: Mapped[TypeMission] = relationship(back_populates="missions")
    secteur: Mapped[Secteur | None] = relationship(
        back_populates="missions",
        foreign_keys=[secteur_id]
    )
    secteur_depart: Mapped[Secteur | None] = relationship(
        back_populates="missions_depart",
        foreign_keys=[secteur_depart_id]
    )
    secteur_arrivee: Mapped[Secteur | None] = relationship(
        back_populates="missions_arrivee",
        foreign_keys=[secteur_arrivee_id]
    )
    grades_autorises: Mapped[list[Grade]] = relationship(
        secondary=mission_grades,
        back_populates="missions_autorisees"
    )
    affectations: Mapped[list[Affectation]] = relationship(
        back_populates="mission"
    )


class Affectation(Base):
    __tablename__ = "affectations"

    __table_args__ = (
        CheckConstraint(
            "statut IN ('proposee', 'acceptee', 'en_cours', 'validee', 'refusee', 'annulee')",
            name="ck_affectations_statut"
        ),
        CheckConstraint(
            "nb_livraisons_formation_validees IS NULL OR "
            "nb_livraisons_formation_validees BETWEEN 0 AND 3",
            name="ck_affectations_livraisons_formation"
        ),
        CheckConstraint(
            "prime_po IS NULL OR prime_po >= 0",
            name="ck_affectations_prime"
        ),
        UniqueConstraint(
            "mission_id",
            "personnage_id",
            name="uq_affectations_mission_personnage"
        ),
        Index("ix_affectations_personnage_id", "personnage_id"),
        Index("ix_affectations_recrue_personnage_id", "recrue_personnage_id"),
        Index("ix_affectations_statut", "statut"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mission_id: Mapped[int] = mapped_column(
        ForeignKey("missions.id", ondelete="RESTRICT"),
        nullable=False
    )
    personnage_id: Mapped[int] = mapped_column(
        ForeignKey("personnages.id", ondelete="RESTRICT"),
        nullable=False
    )
    recrue_personnage_id: Mapped[int | None] = mapped_column(
        ForeignKey("personnages.id", ondelete="RESTRICT"),
        nullable=True
    )
    nb_livraisons_formation_validees: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )
    prime_po: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prime_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    statut: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="proposee",
        server_default="proposee"
    )
    validee_par_utilisateur_id: Mapped[int | None] = mapped_column(
        ForeignKey("utilisateurs.id", ondelete="RESTRICT"),
        nullable=True
    )
    validee_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    mission: Mapped[Mission] = relationship(back_populates="affectations")
    personnage: Mapped[Personnage] = relationship(
        back_populates="affectations",
        foreign_keys=[personnage_id]
    )
    recrue: Mapped[Personnage | None] = relationship(
        back_populates="affectations_comme_recrue",
        foreign_keys=[recrue_personnage_id]
    )

