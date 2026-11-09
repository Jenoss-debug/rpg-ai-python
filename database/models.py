
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func
)
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


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

