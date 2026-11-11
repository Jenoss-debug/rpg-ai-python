from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from database.models import Utilisateur
from dependencies.auth import obtenir_utilisateur_connecte
from routers.templates import templates


router = APIRouter()


@router.get("/")
def accueil(
    request: Request,
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_connecte)
):
    if utilisateur is None:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"utilisateur": utilisateur}
    )
