from fastapi import APIRouter, Depends

from database.models import Utilisateur
from dependencies.auth import exiger_connexion


router = APIRouter()


@router.get("/espace-prive")
def espace_prive(
    utilisateur: Utilisateur = Depends(exiger_connexion)
):
    return {
        "message": "Bienvenue dans l'espace privé !",
        "utilisateur": utilisateur.username,
        "role": utilisateur.role
    }
