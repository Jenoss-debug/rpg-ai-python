import os

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from database.connexion import get_db
from database.models import Utilisateur


# Application
serveur_rpg = FastAPI()

# Clé secrète obligatoire pour signer les sessions
SESSION_SECRET = os.getenv("SESSION_SECRET")
if not SESSION_SECRET:
    raise RuntimeError("La variable SESSION_SECRET n'est pas définie.")

# Gestion des sessions
serveur_rpg.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="rpg_session",
    max_age=8 * 60 * 60,  # 8 heures
    same_site="lax",
    https_only=os.getenv("APP_ENV") == "production"
)

# Fichiers statiques et templates
serveur_rpg.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

templates = Jinja2Templates(directory="templates")

# Vérification des mots de passe
hasher = PasswordHasher()


def obtenir_utilisateur_connecte(
    request: Request,
    db: Session = Depends(get_db)
):
    """Retourne l'utilisateur connecté, ou None."""

    user_id = request.session.get("user_id")

    if user_id is None:
        return None

    utilisateur = db.get(Utilisateur, user_id)

    if utilisateur is None or not utilisateur.is_active:
        request.session.clear()
        return None

    return utilisateur


def exiger_connexion(
    utilisateur: Utilisateur = Depends(obtenir_utilisateur_connecte)
):
    """Refuse l'accès si l'utilisateur n'est pas connecté."""

    if utilisateur is None:
        raise HTTPException(
            status_code=401,
            detail="Authentification requise."
        )

    return utilisateur


def exiger_admin(
    utilisateur: Utilisateur = Depends(exiger_connexion)
):
    """Réserve l'accès aux administrateurs."""

    if utilisateur.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Accès réservé aux administrateurs."
        )

    return utilisateur


@serveur_rpg.get("/")
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


@serveur_rpg.get("/login")
def afficher_login(request: Request):
    if request.session.get("user_id") is not None:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"erreur": None}
    )


@serveur_rpg.post("/login")
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


@serveur_rpg.post("/logout")
def deconnecter(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@serveur_rpg.get("/espace-prive")
def espace_prive(
    utilisateur: Utilisateur = Depends(exiger_connexion)
):
    return {
        "message": "Bienvenue dans l'espace privé !",
        "utilisateur": utilisateur.username,
        "role": utilisateur.role
    }


@serveur_rpg.get("/admin/test")
def test_admin(
    utilisateur: Utilisateur = Depends(exiger_admin)
):
    return {
        "message": "Accès administrateur autorisé !",
        "utilisateur": utilisateur.username
    }