from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database.connexion import get_db
from database.models import Utilisateur


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


def exiger_coursier(
    utilisateur: Utilisateur = Depends(exiger_connexion)
):
    """Réserve l'accès aux coursiers."""

    if utilisateur.role != "coursier":
        raise HTTPException(
            status_code=403,
            detail="Accès réservé aux coursiers."
        )

    return utilisateur
