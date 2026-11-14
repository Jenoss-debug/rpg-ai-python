from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from database.connexion import get_db
from database.models import Carte, CaseCarte, Utilisateur
from dependencies.auth import exiger_acces_preparation_itineraires, exiger_admin
from routers.templates import templates


router = APIRouter()
TERRAINS_AUTORISES = frozenset({
    "plain",
    "desert",
    "forest",
    "deep_forest",
    "sea",
    "deep_water",
    "coal",
    "cloud",
    "mountain",
    "road",
    "city",
})


class CasePeinte(BaseModel):
    x: int = Field(strict=True, ge=0)
    y: int = Field(strict=True, ge=0)
    terrain_code: str = Field(strict=True, min_length=1, max_length=40)
    variant: int = Field(strict=True, ge=1, le=4)


class CarteAvecCases(BaseModel):
    code: str
    nom: str
    largeur: int
    hauteur: int
    cases: list[CasePeinte]


def _est_meme_origine(request: Request) -> bool:
    origine = request.headers.get("origin")
    est_referer = origine is None
    if origine is None:
        origine = request.headers.get("referer")
    if origine is None:
        return False

    try:
        source = urlsplit(origine)
        source_port = source.port
        cible_port = request.url.port
    except ValueError:
        return False

    if (
        source.scheme.lower() not in {"http", "https"}
        or source.hostname is None
        or source.username is not None
        or source.password is not None
        or (not est_referer and (
            source.path not in {"", "/"}
            or source.query
            or source.fragment
        ))
    ):
        return False

    scheme = request.url.scheme.lower()
    if source.scheme.lower() != scheme:
        return False

    if source_port is None:
        source_port = 443 if source.scheme.lower() == "https" else 80
    if cible_port is None:
        cible_port = 443 if scheme == "https" else 80
    return (
        source.hostname.lower() == request.url.hostname.lower()
        and source_port == cible_port
    )


def _obtenir_carte_terres_neutres(db: Session) -> Carte:
    carte = db.scalar(
        select(Carte).where(Carte.code == "terres_neutres")
    )
    if carte is None:
        raise HTTPException(
            status_code=404,
            detail="La carte terres_neutres est introuvable."
        )
    return carte


@router.get(
    "/api/admin/cartes/terres_neutres",
    response_model=CarteAvecCases
)
def lire_carte_terres_neutres(
    utilisateur: Utilisateur = Depends(exiger_acces_preparation_itineraires),
    db: Session = Depends(get_db)
):
    carte = _obtenir_carte_terres_neutres(db)
    cases = db.scalars(
        select(CaseCarte)
        .where(CaseCarte.carte_id == carte.id)
        .order_by(CaseCarte.x, CaseCarte.y)
    ).all()

    return {
        "code": carte.code,
        "nom": carte.nom,
        "largeur": carte.largeur,
        "hauteur": carte.hauteur,
        "cases": [
            {
                "x": case.x,
                "y": case.y,
                "terrain_code": case.terrain_code,
                "variant": case.variant,
            }
            for case in cases
        ],
    }


@router.put(
    "/api/admin/cartes/terres_neutres",
    response_model=CarteAvecCases
)
def enregistrer_carte_terres_neutres(
    cases: list[CasePeinte],
    request: Request,
    utilisateur: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    if not _est_meme_origine(request):
        raise HTTPException(
            status_code=403,
            detail="Origine de la requête non autorisée."
        )

    carte = _obtenir_carte_terres_neutres(db)
    coordonnees = set()
    for case in cases:
        if case.x >= carte.largeur or case.y >= carte.hauteur:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Coordonnées hors limites pour la case "
                    f"({case.x}, {case.y})."
                )
            )
        if case.terrain_code not in TERRAINS_AUTORISES:
            raise HTTPException(
                status_code=422,
                detail=f"Code de terrain inconnu : {case.terrain_code}."
            )
        coordonnee = (case.x, case.y)
        if coordonnee in coordonnees:
            raise HTTPException(
                status_code=422,
                detail=f"Coordonnées dupliquées : ({case.x}, {case.y})."
            )
        coordonnees.add(coordonnee)

    try:
        db.execute(
            delete(CaseCarte).where(CaseCarte.carte_id == carte.id)
        )
        db.add_all([
            CaseCarte(
                carte_id=carte.id,
                x=case.x,
                y=case.y,
                terrain_code=case.terrain_code,
                variant=case.variant,
            )
            for case in cases
        ])
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "code": carte.code,
        "nom": carte.nom,
        "largeur": carte.largeur,
        "hauteur": carte.hauteur,
        "cases": cases,
    }


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
