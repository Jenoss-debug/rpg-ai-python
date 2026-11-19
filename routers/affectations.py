from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from database.connexion import get_db
from database.models import (
    Affectation,
    Grade,
    Mission,
    Personnage,
    Utilisateur
)
from dependencies.auth import exiger_gestion_affectations
from routers.templates import templates


router = APIRouter()
STATUTS_AFFECTATION = {
    "en_cours": "En cours",
    "terminee": "Terminée",
    "revoquee": "Révoquée"
}


def charger_mission(db: Session, mission_id: int) -> Mission:
    mission = db.scalar(
        select(Mission)
        .options(
            selectinload(Mission.type_mission),
            selectinload(Mission.secteur),
            selectinload(Mission.carte),
            selectinload(Mission.grades_autorises)
        )
        .where(Mission.id == mission_id)
    )
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission introuvable.")
    return mission


def charger_donnees_affectations(
    db: Session,
    mission: Mission
) -> tuple[list[Affectation], list[Personnage]]:
    affectations = db.scalars(
        select(Affectation)
        .options(
            selectinload(Affectation.personnage).selectinload(Personnage.grade),
            selectinload(Affectation.personnage).selectinload(Personnage.compte)
        )
        .where(Affectation.mission_id == mission.id)
        .order_by(Affectation.created_at, Affectation.id)
    ).all()
    personnages_affectes = {affectation.personnage_id for affectation in affectations}
    grades_autorises = {grade.id for grade in mission.grades_autorises}
    if not grades_autorises:
        return affectations, []

    requete_personnages = (
        select(Personnage)
        .join(Grade, Personnage.grade_id == Grade.id)
        .options(
            selectinload(Personnage.grade),
            selectinload(Personnage.compte)
        )
        .where(Grade.id.in_(grades_autorises))
        .order_by(Personnage.matricule, Personnage.id)
    )
    if personnages_affectes:
        requete_personnages = requete_personnages.where(
            Personnage.id.not_in(personnages_affectes)
        )
    personnages_disponibles = db.scalars(requete_personnages).all()
    return affectations, personnages_disponibles


def rendre_fiche_affectations(
    request: Request,
    utilisateur: Utilisateur,
    db: Session,
    mission: Mission,
    erreur: str | None = None,
    status_code: int = 200
):
    affectations, personnages_disponibles = charger_donnees_affectations(
        db,
        mission
    )
    return templates.TemplateResponse(
        request=request,
        name="affectations_mission.html",
        context={
            "utilisateur": utilisateur,
            "peut_preparer_itineraires": False,
            "peut_gerer_affectations": True,
            "mission": mission,
            "affectations": affectations,
            "personnages_disponibles": personnages_disponibles,
            "statuts_affectation": STATUTS_AFFECTATION,
            "erreur": erreur
        },
        status_code=status_code
    )


@router.get("/affectations")
def liste_missions_affectations(
    request: Request,
    utilisateur: Utilisateur = Depends(exiger_gestion_affectations),
    db: Session = Depends(get_db)
):
    missions = db.scalars(
        select(Mission)
        .options(selectinload(Mission.type_mission))
        .order_by(Mission.created_at.desc(), Mission.id.desc())
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="affectations_missions.html",
        context={
            "utilisateur": utilisateur,
            "peut_preparer_itineraires": False,
            "peut_gerer_affectations": True,
            "missions": missions,
            "statuts_mission": {
                "brouillon": "Brouillon",
                "ouverte": "Ouverte",
                "en_cours": "En cours",
                "terminee": "Terminée",
                "annulee": "Annulée"
            }
        }
    )


@router.get("/affectations/missions/{mission_id}")
def fiche_mission_affectations(
    request: Request,
    mission_id: int,
    utilisateur: Utilisateur = Depends(exiger_gestion_affectations),
    db: Session = Depends(get_db)
):
    mission = charger_mission(db, mission_id)
    return rendre_fiche_affectations(request, utilisateur, db, mission)


@router.post("/affectations/missions/{mission_id}")
def creer_affectations(
    request: Request,
    mission_id: int,
    personnage_ids: list[int] = Form(...),
    utilisateur: Utilisateur = Depends(exiger_gestion_affectations),
    db: Session = Depends(get_db)
):
    mission = charger_mission(db, mission_id)
    if not personnage_ids:
        return rendre_fiche_affectations(
            request,
            utilisateur,
            db,
            mission,
            erreur="Sélectionnez au moins un personnage.",
            status_code=400
        )
    if len(personnage_ids) != len(set(personnage_ids)):
        return rendre_fiche_affectations(
            request,
            utilisateur,
            db,
            mission,
            erreur="Un personnage est présent plusieurs fois dans la sélection.",
            status_code=400
        )

    grades_autorises = {grade.id for grade in mission.grades_autorises}
    if not grades_autorises:
        return rendre_fiche_affectations(
            request,
            utilisateur,
            db,
            mission,
            erreur="Aucun grade n’est autorisé pour cette mission.",
            status_code=400
        )

    personnages = db.scalars(
        select(Personnage)
        .options(selectinload(Personnage.grade))
        .where(Personnage.id.in_(personnage_ids))
    ).all()
    if len(personnages) != len(personnage_ids):
        return rendre_fiche_affectations(
            request,
            utilisateur,
            db,
            mission,
            erreur="Un personnage sélectionné est introuvable.",
            status_code=404
        )

    incompatibles = [
        personnage for personnage in personnages
        if personnage.grade_id not in grades_autorises
    ]
    if incompatibles:
        matricules = ", ".join(
            personnage.matricule for personnage in incompatibles
        )
        return rendre_fiche_affectations(
            request,
            utilisateur,
            db,
            mission,
            erreur=f"Le grade du ou des personnages suivants n’est pas autorisé : {matricules}.",
            status_code=400
        )

    deja_affectes = set(db.scalars(
        select(Affectation.personnage_id).where(
            Affectation.mission_id == mission.id,
            Affectation.personnage_id.in_(personnage_ids)
        )
    ).all())
    if deja_affectes:
        matricules = ", ".join(
            personnage.matricule
            for personnage in personnages
            if personnage.id in deja_affectes
        )
        return rendre_fiche_affectations(
            request,
            utilisateur,
            db,
            mission,
            erreur=f"Une affectation existe déjà pour : {matricules}.",
            status_code=409
        )

    db.add_all([
        Affectation(
            mission_id=mission.id,
            personnage_id=personnage.id,
            statut="en_cours"
        )
        for personnage in personnages
    ])
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        mission = charger_mission(db, mission_id)
        conflits = set(db.scalars(
            select(Affectation.personnage_id).where(
                Affectation.mission_id == mission.id,
                Affectation.personnage_id.in_(personnage_ids)
            )
        ).all())
        if not conflits:
            raise
        matricules = ", ".join(
            personnage.matricule
            for personnage in personnages
            if personnage.id in conflits
        )
        return rendre_fiche_affectations(
            request,
            utilisateur,
            db,
            mission,
            erreur=f"Une affectation vient d’être créée en parallèle pour : {matricules}.",
            status_code=409
        )

    return RedirectResponse(
        url=f"/affectations/missions/{mission.id}",
        status_code=303
    )


@router.post("/affectations/{affectation_id}/statut")
def modifier_statut_affectation(
    affectation_id: int,
    statut: str = Form(...),
    utilisateur: Utilisateur = Depends(exiger_gestion_affectations),
    db: Session = Depends(get_db)
):
    affectation = db.get(Affectation, affectation_id)
    if affectation is None:
        raise HTTPException(
            status_code=404,
            detail="Affectation introuvable."
        )
    if statut not in STATUTS_AFFECTATION:
        raise HTTPException(
            status_code=422,
            detail="Statut d’affectation non autorisé."
        )

    affectation.statut = statut
    db.commit()
    destination = (
        f"/admin/missions/{affectation.mission_id}"
        if utilisateur.role == "admin"
        else f"/affectations/missions/{affectation.mission_id}"
    )
    return RedirectResponse(url=destination, status_code=303)
