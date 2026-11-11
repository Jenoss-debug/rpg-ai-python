from fastapi import APIRouter, Depends

from database.models import Utilisateur
from dependencies.auth import exiger_admin


router = APIRouter()


@router.get("/admin/test")
def test_admin(
    utilisateur: Utilisateur = Depends(exiger_admin)
):
    return {
        "message": "Accès administrateur autorisé !",
        "utilisateur": utilisateur.username
    }
