from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.connexion import get_db
from database.models import Livraison, Utilisateur
from dependencies.auth import (
    a_personnage_avec_grade,
    exiger_admin,
    exiger_acces_preparation_itineraires,
    exiger_coursier,
    obtenir_utilisateur_connecte
)
from routers.templates import templates


router = APIRouter()
LIBELLES_STATUTS = {
    "a_preparer": "À préparer",
    "en_cours": "En cours",
    "livree": "Livrée"
}


@router.get("/")
def accueil(
    request: Request,
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_connecte),
    db: Session = Depends(get_db)
):
    if utilisateur is None:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "utilisateur": utilisateur,
            "peut_preparer_itineraires": (
                utilisateur.role == "admin"
                or a_personnage_avec_grade(utilisateur, db)
            )
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
            "peut_preparer_itineraires": a_personnage_avec_grade(
                utilisateur,
                db
            )
        }
    )


@router.get("/preparation-itineraires")
def preparation_itineraires(
    request: Request,
    utilisateur: Utilisateur = Depends(exiger_acces_preparation_itineraires)
):
    return templates.TemplateResponse(
        request=request,
        name="route_planner.html",
        context={
            "utilisateur": utilisateur,
            "peut_preparer_itineraires": True
        }
    )
