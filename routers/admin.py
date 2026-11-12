from fastapi import APIRouter, Depends, Request

from database.models import Utilisateur
from dependencies.auth import exiger_admin
from routers.templates import templates


router = APIRouter()


@router.get("/admin/cartes")
def administration_cartes(
    request: Request,
    utilisateur: Utilisateur = Depends(exiger_admin)
):
    return templates.TemplateResponse(
        request=request,
        name="admin_cartes.html",
        context={
            "utilisateur": utilisateur,
            "peut_preparer_itineraires": True
        }
    )


@router.get("/admin/test")
def test_admin(
    utilisateur: Utilisateur = Depends(exiger_admin)
):
    return {
        "message": "Accès administrateur autorisé !",
        "utilisateur": utilisateur.username
    }
