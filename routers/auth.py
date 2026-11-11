from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.connexion import get_db
from database.models import Utilisateur
from routers.templates import templates


router = APIRouter()
hasher = PasswordHasher()


@router.get("/login")
def afficher_login(request: Request):
    if request.session.get("user_id") is not None:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"erreur": None}
    )


@router.post("/login")
def connecter(
    request: Request,
    identifiant: str = Form(...),
    mot_de_passe: str = Form(...),
    db: Session = Depends(get_db)
):
    utilisateur = db.scalar(
        select(Utilisateur).where(
            (Utilisateur.username == identifiant.strip())
            | (Utilisateur.email == identifiant.strip().lower())
        )
    )

    # Message volontairement identique si le compte n'existe pas
    # ou si le mot de passe est incorrect.
    mot_de_passe_valide = False

    if utilisateur is not None and utilisateur.is_active:
        try:
            mot_de_passe_valide = hasher.verify(
                utilisateur.password_hash,
                mot_de_passe
            )
        except (VerifyMismatchError, InvalidHashError):
            mot_de_passe_valide = False

    if not mot_de_passe_valide:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"erreur": "Identifiant ou mot de passe incorrect."},
            status_code=401
        )

    # On renouvelle la session avant de connecter l'utilisateur.
    request.session.clear()
    request.session["user_id"] = utilisateur.id

    return RedirectResponse(url="/", status_code=303)


@router.post("/logout")
def deconnecter(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
