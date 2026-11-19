from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.connexion import get_db
from database.models import Livraison, Mission, Utilisateur
from dependencies.auth import (
    exiger_admin,
    exiger_acces_preparation_itineraires,
    exiger_coursier,
    peut_gerer_affectations,
    obtenir_utilisateur_connecte,
    peut_preparer_itineraires
)
from routers.templates import templates


router = APIRouter()
LIBELLES_STATUTS = {
    "a_preparer": "À préparer",
    "en_cours": "En cours",
    "livree": "Livrée"
}


def _charger_missions_publiques_ouvertes(
    db: Session,
    limite: int | None = None
) -> list[dict[str, str | None]]:
    requete = (
        select(Mission.titre, Mission.description_publique)
        .where(
            Mission.publique.is_(True),
            Mission.statut == "ouverte"
        )
        .order_by(Mission.created_at.desc(), Mission.id.desc())
    )
    if limite is not None:
        requete = requete.limit(limite)
    lignes = db.execute(requete).mappings()
    return [
        {
            "titre": ligne["titre"],
            "description_publique": ligne["description_publique"]
        }
        for ligne in lignes
    ]


@router.get("/")
def accueil(
    request: Request,
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_connecte),
    db: Session = Depends(get_db)
):
    if utilisateur is not None:
        if utilisateur.role == "admin":
            return RedirectResponse(url="/admin", status_code=303)
        if utilisateur.role == "coursier":
            return RedirectResponse(url="/coursier", status_code=303)
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="public_home.html",
        context={
            "utilisateur": None,
            "missions": _charger_missions_publiques_ouvertes(db, limite=3)
        }
    )


@router.get("/annonces")
def annonces_publiques(
    request: Request,
    db: Session = Depends(get_db)
):
    return templates.TemplateResponse(
        request=request,
        name="public_announcements.html",
        context={
            "utilisateur": None,
            "missions": _charger_missions_publiques_ouvertes(db)
        }
    )


@router.get("/admin")
def tableau_admin(
    request: Request,
    utilisateur: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    nombre_coursiers = db.scalar(
        select(func.count()).select_from(Utilisateur).where(
            Utilisateur.role == "coursier"
        )
    )
    nombre_livraisons = db.scalar(
        select(func.count()).select_from(Livraison)
    )

    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "utilisateur": utilisateur,
            "nombre_coursiers": nombre_coursiers,
            "nombre_livraisons": nombre_livraisons,
            "peut_preparer_itineraires": True
        }
    )


@router.get("/coursier")
def tableau_coursier(
    request: Request,
    utilisateur: Utilisateur = Depends(exiger_coursier),
    db: Session = Depends(get_db)
):
    livraisons = db.scalars(
        select(Livraison)
        .where(Livraison.coursier_id == utilisateur.id)
        .order_by(Livraison.created_at.desc())
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="courier_dashboard.html",
        context={
            "utilisateur": utilisateur,
            "livraisons": livraisons,
            "libelles_statuts": LIBELLES_STATUTS,
            "peut_preparer_itineraires": peut_preparer_itineraires(
                utilisateur,
                db
            ),
            "peut_gerer_affectations": peut_gerer_affectations(
                utilisateur,
                db
            )
        }
    )


@router.get("/preparation-itineraires")
def preparation_itineraires(
    request: Request,
    utilisateur: Utilisateur = Depends(exiger_acces_preparation_itineraires),
    db: Session = Depends(get_db)
):
    return templates.TemplateResponse(
        request=request,
        name="route_planner.html",
        context={
            "utilisateur": utilisateur,
            "peut_preparer_itineraires": True,
            "peut_gerer_affectations": peut_gerer_affectations(
                utilisateur,
                db
            )
        }
    )
