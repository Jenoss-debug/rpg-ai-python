from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from database.connexion import get_db
from database.models import Carte, Grade, Mission, Secteur, TypeMission, Utilisateur
from dependencies.auth import exiger_admin
from routers.affectations import (
    STATUTS_AFFECTATION,
    charger_donnees_affectations
)
from routers.templates import templates


router = APIRouter()
STATUTS_MISSION = {
    "brouillon": "Brouillon",
    "ouverte": "Ouverte",
    "en_cours": "En cours",
    "terminee": "Terminée",
    "annulee": "Annulée"
}


def _obtenir_mission(db: Session, mission_id: int) -> Mission:
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


def _parser_identifiant_optionnel(
    valeur: str,
    libelle: str
) -> tuple[int | None, str | None]:
    valeur = valeur.strip()
    if not valeur:
        return None, None
    try:
        return int(valeur), None
    except ValueError:
        return None, f"Le choix « {libelle} » est invalide."


def _valider_coordonnees(
    db: Session,
    carte_id: int,
    valeurs: tuple[str | None, str | None, str | None, str | None],
    valeurs_existantes: tuple[
        int | None, int | None, int | None, int | None
    ] = (None, None, None, None)
) -> tuple[
    Carte | None,
    tuple[int | None, int | None, int | None, int | None],
    str | None
]:
    carte = db.get(Carte, carte_id)
    if carte is None:
        return None, valeurs_existantes, "La carte sélectionnée est introuvable."

    coordonnees: list[int | None] = []
    for valeur, existante, axe, libelle in zip(
        valeurs,
        valeurs_existantes,
        ("x", "y", "x", "y"),
        ("départ X", "départ Y", "arrivée X", "arrivée Y")
    ):
        if valeur is None:
            coordonnee = existante
        elif not valeur.strip():
            coordonnee = None
        else:
            try:
                coordonnee = int(valeur)
            except ValueError:
                return carte, valeurs_existantes, f"La coordonnée {libelle} doit être un entier."
        if coordonnee is not None:
            limite = carte.largeur if axe == "x" else carte.hauteur
            if not 0 <= coordonnee < limite:
                return (
                    carte,
                    valeurs_existantes,
                    f"La coordonnée {libelle} doit être comprise entre 0 et {limite - 1}."
                )
        coordonnees.append(coordonnee)

    return carte, (
        coordonnees[0],
        coordonnees[1],
        coordonnees[2],
        coordonnees[3]
    ), None


def _charger_references(
    db: Session,
    type_mission_id: int,
    secteur_id: str,
    grade_ids: list[int]
) -> tuple[TypeMission | None, Secteur | None, list[Grade], str | None]:
    type_mission = db.get(TypeMission, type_mission_id)
    if type_mission is None:
        return None, None, [], "Le type de mission est introuvable."

    secteur_identifiant, erreur = _parser_identifiant_optionnel(
        secteur_id,
        "secteur"
    )
    if erreur:
        return None, None, [], erreur
    secteur = (
        db.get(Secteur, secteur_identifiant)
        if secteur_identifiant is not None
        else None
    )
    if secteur_identifiant is not None and secteur is None:
        return None, None, [], "Le secteur sélectionné est introuvable."

    grade_ids_uniques = set(grade_ids)
    grades = (
        db.scalars(
            select(Grade)
            .where(Grade.id.in_(grade_ids_uniques))
            .order_by(Grade.rang)
        ).all()
        if grade_ids_uniques
        else []
    )
    if len(grades) != len(grade_ids_uniques):
        return None, None, [], "Un grade sélectionné est introuvable."

    return type_mission, secteur, grades, None


def _rendre_formulaire_mission(
    request: Request,
    administrateur: Utilisateur,
    db: Session,
    mode: str,
    titre: str = "",
    description: str = "",
    description_publique: str = "",
    publique: bool = False,
    type_mission_id: int | None = None,
    secteur_id: str = "",
    carte_id: int | None = None,
    depart_x: str | int | None = None,
    depart_y: str | int | None = None,
    arrivee_x: str | int | None = None,
    arrivee_y: str | int | None = None,
    recompense_po: str = "",
    statut: str = "brouillon",
    grade_ids: list[int] | None = None,
    mission_id: int | None = None,
    erreur: str | None = None,
    status_code: int = 200
):
    if carte_id is None:
        carte_par_defaut = db.scalar(
            select(Carte).where(Carte.code == "terres_neutres")
        )
        if carte_par_defaut is None:
            raise HTTPException(
                status_code=500,
                detail="La carte Terres neutres est absente."
            )
        carte_id = carte_par_defaut.id

    return templates.TemplateResponse(
        request=request,
        name="admin_mission_form.html",
        context={
            "utilisateur": administrateur,
            "peut_preparer_itineraires": True,
            "mode": mode,
            "titre": titre,
            "description": description,
            "description_publique": description_publique,
            "publique": publique,
            "type_mission_id": type_mission_id,
            "secteur_id": secteur_id,
            "carte_id": carte_id,
            "depart_x": depart_x,
            "depart_y": depart_y,
            "arrivee_x": arrivee_x,
            "arrivee_y": arrivee_y,
            "recompense_po": recompense_po,
            "statut": statut,
            "grade_ids": grade_ids or [],
            "mission_id": mission_id,
            "erreur": erreur,
            "types_missions": db.scalars(
                select(TypeMission).order_by(TypeMission.nom)
            ).all(),
            "secteurs": db.scalars(
                select(Secteur).order_by(Secteur.nom)
            ).all(),
            "cartes": db.scalars(select(Carte).order_by(Carte.nom)).all(),
            "grades": db.scalars(
                select(Grade).order_by(Grade.rang)
            ).all(),
            "libelles_statuts": STATUTS_MISSION
        },
        status_code=status_code
    )


def _valider_champs(
    titre: str,
    description: str,
    recompense_po: str,
    statut: str
) -> tuple[str, str, int | None, str | None]:
    titre = titre.strip()
    description = description.strip()
    if not titre:
        return titre, description, None, "Le titre est obligatoire."
    if len(titre) > 150:
        return titre, description, None, "Le titre ne peut pas dépasser 150 caractères."
    if not description:
        return titre, description, None, "La description est obligatoire."
    if statut not in STATUTS_MISSION:
        return titre, description, None, "Le statut sélectionné est invalide."

    valeur_recompense = recompense_po.strip()
    if not valeur_recompense:
        return titre, description, None, None
    try:
        recompense = int(valeur_recompense)
    except ValueError:
        return titre, description, None, "La récompense doit être un nombre entier."
    if recompense < 0:
        return titre, description, None, "La récompense ne peut pas être négative."

    return titre, description, recompense, None


def _charger_liste_missions(db: Session) -> list[Mission]:
    return db.scalars(
        select(Mission)
        .options(
            selectinload(Mission.type_mission),
            selectinload(Mission.secteur),
            selectinload(Mission.carte)
        )
        .order_by(Mission.created_at.desc(), Mission.id.desc())
    ).all()


@router.get("/admin/missions")
def liste_missions(
    request: Request,
    administrateur: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    return templates.TemplateResponse(
        request=request,
        name="admin_missions.html",
        context={
            "utilisateur": administrateur,
            "peut_preparer_itineraires": True,
            "missions": _charger_liste_missions(db),
            "libelles_statuts": STATUTS_MISSION
        }
    )


@router.get("/admin/missions/nouveau")
def formulaire_nouvelle_mission(
    request: Request,
    administrateur: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    return _rendre_formulaire_mission(
        request,
        administrateur,
        db,
        mode="creation"
    )


@router.post("/admin/missions")
def creer_mission(
    request: Request,
    titre: str = Form(...),
    description: str = Form(...),
    type_mission_id: int = Form(...),
    statut: str = Form("brouillon"),
    description_publique: str = Form(""),
    publique: bool = Form(False),
    secteur_id: str = Form(""),
    carte_id: int = Form(...),
    depart_x: str | None = Form(None),
    depart_y: str | None = Form(None),
    arrivee_x: str | None = Form(None),
    arrivee_y: str | None = Form(None),
    recompense_po: str = Form(""),
    grade_ids: list[int] = Form([]),
    administrateur: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    titre, description, recompense, erreur = _valider_champs(
        titre, description, recompense_po, statut
    )
    type_mission, secteur, grades, erreur_refs = _charger_references(
        db, type_mission_id, secteur_id, grade_ids
    )
    carte, coordonnees, erreur_coordonnees = _valider_coordonnees(
        db,
        carte_id,
        (depart_x, depart_y, arrivee_x, arrivee_y)
    )
    if erreur is None:
        erreur = erreur_refs or erreur_coordonnees

    if erreur:
        return _rendre_formulaire_mission(
            request,
            administrateur,
            db,
            mode="creation",
            titre=titre,
            description=description,
            description_publique=description_publique,
            publique=publique,
            type_mission_id=type_mission_id,
            secteur_id=secteur_id,
            carte_id=carte_id,
            depart_x=depart_x,
            depart_y=depart_y,
            arrivee_x=arrivee_x,
            arrivee_y=arrivee_y,
            recompense_po=recompense_po,
            statut=statut,
            grade_ids=grade_ids,
            erreur=erreur,
            status_code=400
        )

    mission = Mission(
        titre=titre,
        description=description,
        description_publique=description_publique.strip() or None,
        publique=publique,
        type_mission=type_mission,
        secteur=secteur,
        carte=carte,
        depart_x=coordonnees[0],
        depart_y=coordonnees[1],
        arrivee_x=coordonnees[2],
        arrivee_y=coordonnees[3],
        recompense_po=recompense,
        statut=statut,
        cree_par_utilisateur_id=administrateur.id,
        grades_autorises=grades
    )
    db.add(mission)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return _rendre_formulaire_mission(
            request,
            administrateur,
            db,
            mode="creation",
            titre=titre,
            description=description,
            description_publique=description_publique,
            publique=publique,
            type_mission_id=type_mission_id,
            secteur_id=secteur_id,
            carte_id=carte_id,
            depart_x=depart_x,
            depart_y=depart_y,
            arrivee_x=arrivee_x,
            arrivee_y=arrivee_y,
            recompense_po=recompense_po,
            statut=statut,
            grade_ids=grade_ids,
            erreur="Une référence sélectionnée n’est plus valide.",
            status_code=409
        )

    return RedirectResponse(
        url=f"/admin/missions/{mission.id}",
        status_code=303
    )


@router.get("/admin/missions/{mission_id}")
def fiche_mission(
    request: Request,
    mission_id: int,
    administrateur: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    mission = _obtenir_mission(db, mission_id)
    affectations, personnages_disponibles = charger_donnees_affectations(
        db,
        mission
    )
    return templates.TemplateResponse(
        request=request,
        name="admin_mission_detail.html",
        context={
            "utilisateur": administrateur,
            "peut_preparer_itineraires": True,
            "mission": mission,
            "affectations": affectations,
            "personnages_disponibles": personnages_disponibles,
            "statuts_affectation": STATUTS_AFFECTATION,
            "peut_gerer_affectations": True,
            "libelle_statut": STATUTS_MISSION[mission.statut],
            "grades_autorises": sorted(
                mission.grades_autorises,
                key=lambda grade: grade.rang
            )
        }
    )


@router.get("/admin/missions/{mission_id}/modifier")
def formulaire_modifier_mission(
    request: Request,
    mission_id: int,
    administrateur: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    mission = _obtenir_mission(db, mission_id)
    return _rendre_formulaire_mission(
        request,
        administrateur,
        db,
        mode="modification",
        titre=mission.titre,
        description=mission.description,
        description_publique=mission.description_publique or "",
        publique=mission.publique,
        type_mission_id=mission.type_mission_id,
        secteur_id=str(mission.secteur_id or ""),
        carte_id=mission.carte_id,
        depart_x=mission.depart_x,
        depart_y=mission.depart_y,
        arrivee_x=mission.arrivee_x,
        arrivee_y=mission.arrivee_y,
        recompense_po=(
            str(mission.recompense_po)
            if mission.recompense_po is not None
            else ""
        ),
        statut=mission.statut,
        grade_ids=[grade.id for grade in mission.grades_autorises],
        mission_id=mission.id
    )


@router.post("/admin/missions/{mission_id}/modifier")
def modifier_mission(
    request: Request,
    mission_id: int,
    titre: str = Form(...),
    description: str = Form(...),
    type_mission_id: int = Form(...),
    statut: str = Form("brouillon"),
    description_publique: str = Form(""),
    publique: bool = Form(False),
    secteur_id: str = Form(""),
    carte_id: int = Form(...),
    depart_x: str | None = Form(None),
    depart_y: str | None = Form(None),
    arrivee_x: str | None = Form(None),
    arrivee_y: str | None = Form(None),
    recompense_po: str = Form(""),
    grade_ids: list[int] = Form([]),
    administrateur: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    mission = _obtenir_mission(db, mission_id)
    titre, description, recompense, erreur = _valider_champs(
        titre, description, recompense_po, statut
    )
    type_mission, secteur, grades, erreur_refs = _charger_references(
        db, type_mission_id, secteur_id, grade_ids
    )
    carte, coordonnees, erreur_coordonnees = _valider_coordonnees(
        db,
        carte_id,
        (depart_x, depart_y, arrivee_x, arrivee_y),
        (
            mission.depart_x,
            mission.depart_y,
            mission.arrivee_x,
            mission.arrivee_y
        )
    )
    if erreur is None:
        erreur = erreur_refs or erreur_coordonnees

    if erreur:
        return _rendre_formulaire_mission(
            request,
            administrateur,
            db,
            mode="modification",
            titre=titre,
            description=description,
            description_publique=description_publique,
            publique=publique,
            type_mission_id=type_mission_id,
            secteur_id=secteur_id,
            carte_id=carte_id,
            depart_x=depart_x,
            depart_y=depart_y,
            arrivee_x=arrivee_x,
            arrivee_y=arrivee_y,
            recompense_po=recompense_po,
            statut=statut,
            grade_ids=grade_ids,
            mission_id=mission.id,
            erreur=erreur,
            status_code=400
        )

    mission_id = mission.id
    mission.titre = titre
    mission.description = description
    mission.description_publique = description_publique.strip() or None
    mission.publique = publique
    mission.type_mission = type_mission
    mission.secteur = secteur
    mission.carte = carte
    mission.depart_x = coordonnees[0]
    mission.depart_y = coordonnees[1]
    mission.arrivee_x = coordonnees[2]
    mission.arrivee_y = coordonnees[3]
    mission.recompense_po = recompense
    mission.statut = statut
    mission.grades_autorises = grades
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return _rendre_formulaire_mission(
            request,
            administrateur,
            db,
            mode="modification",
            titre=titre,
            description=description,
            description_publique=description_publique,
            publique=publique,
            type_mission_id=type_mission_id,
            secteur_id=secteur_id,
            carte_id=carte_id,
            depart_x=depart_x,
            depart_y=depart_y,
            arrivee_x=arrivee_x,
            arrivee_y=arrivee_y,
            recompense_po=recompense_po,
            statut=statut,
            grade_ids=grade_ids,
            mission_id=mission_id,
            erreur="Une référence sélectionnée n’est plus valide.",
            status_code=409
        )

    return RedirectResponse(
        url=f"/admin/missions/{mission_id}",
        status_code=303
    )
