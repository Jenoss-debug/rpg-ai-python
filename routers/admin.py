from urllib.parse import urlsplit

from argon2 import PasswordHasher
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from database.connexion import get_db
from database.models import Carte, CaseCarte, Grade, Personnage, Utilisateur
from dependencies.auth import exiger_acces_preparation_itineraires, exiger_admin
from routers.templates import templates


router = APIRouter()
hasher = PasswordHasher()
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


def _obtenir_joueur(db: Session, joueur_id: int) -> Utilisateur:
    joueur = db.scalar(
        select(Utilisateur).where(
            Utilisateur.id == joueur_id,
            Utilisateur.role == "coursier"
        )
    )
    if joueur is None:
        raise HTTPException(status_code=404, detail="Joueur introuvable.")
    return joueur


def _lister_joueurs(db: Session) -> list[Utilisateur]:
    return db.scalars(
        select(Utilisateur)
        .where(Utilisateur.role == "coursier")
        .order_by(Utilisateur.is_active.desc(), Utilisateur.username)
    ).all()


def _obtenir_personnage(db: Session, personnage_id: int) -> Personnage:
    personnage = db.scalar(
        select(Personnage)
        .options(
            selectinload(Personnage.compte),
            selectinload(Personnage.grade),
            selectinload(Personnage.createur)
        )
        .where(Personnage.id == personnage_id)
    )
    if personnage is None:
        raise HTTPException(
            status_code=404,
            detail="Personnage introuvable."
        )
    return personnage


def _obtenir_grade_optionnel(
    db: Session,
    grade_id: str
) -> tuple[int | None, str | None]:
    grade_id = grade_id.strip()
    if not grade_id:
        return None, None

    try:
        identifiant = int(grade_id)
    except ValueError:
        return None, "Le grade sélectionné est invalide."

    if db.get(Grade, identifiant) is None:
        return None, "Le grade sélectionné est introuvable."

    return identifiant, None


def _erreur_unicite_matricule(
    db: Session,
    matricule: str,
    personnage_id: int | None = None
) -> str | None:
    conditions = [Personnage.matricule == matricule]
    if personnage_id is not None:
        conditions.append(Personnage.id != personnage_id)
    if db.scalar(select(Personnage.id).where(*conditions)) is not None:
        return "Ce matricule est déjà utilisé."
    return None


def _rendre_formulaire_joueur(
    request: Request,
    administrateur: Utilisateur,
    mode: str,
    username: str = "",
    email: str = "",
    joueur_id: int | None = None,
    erreur: str | None = None,
    status_code: int = 200
):
    return templates.TemplateResponse(
        request=request,
        name="admin_joueur_form.html",
        context={
            "utilisateur": administrateur,
            "peut_preparer_itineraires": True,
            "mode": mode,
            "username": username,
            "email": email,
            "joueur_id": joueur_id,
            "erreur": erreur
        },
        status_code=status_code
    )


def _rendre_formulaire_personnage(
    request: Request,
    administrateur: Utilisateur,
    db: Session,
    mode: str,
    matricule: str = "",
    nom: str = "",
    joueur_id: int | None = None,
    grade_id: str = "",
    personnage_id: int | None = None,
    erreur: str | None = None,
    status_code: int = 200
):
    return templates.TemplateResponse(
        request=request,
        name="admin_personnage_form.html",
        context={
            "utilisateur": administrateur,
            "peut_preparer_itineraires": True,
            "mode": mode,
            "matricule": matricule,
            "nom": nom,
            "joueur_id": joueur_id,
            "grade_id": grade_id,
            "personnage_id": personnage_id,
            "erreur": erreur,
            "joueurs": _lister_joueurs(db),
            "grades": db.scalars(select(Grade).order_by(Grade.rang)).all()
        },
        status_code=status_code
    )


def _erreur_unicite_joueur(
    db: Session,
    username: str,
    email: str,
    joueur_id: int | None = None
) -> str | None:
    conditions = []
    if joueur_id is not None:
        conditions.append(Utilisateur.id != joueur_id)

    login_existant = db.scalar(
        select(Utilisateur.id).where(
            Utilisateur.username == username,
            *conditions
        )
    )
    if login_existant is not None:
        return "Ce login est déjà utilisé."

    email_existant = db.scalar(
        select(Utilisateur.id).where(
            Utilisateur.email == email,
            *conditions
        )
    )
    if email_existant is not None:
        return "Cette adresse e-mail est déjà utilisée."

    return None


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


@router.get("/admin/joueurs")
def liste_joueurs(
    request: Request,
    administrateur: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    comptes_personnages = (
        select(
            Personnage.utilisateur_id.label("joueur_id"),
            func.count(Personnage.id).label("nombre")
        )
        .group_by(Personnage.utilisateur_id)
        .subquery()
    )
    lignes = db.execute(
        select(
            Utilisateur,
            func.coalesce(comptes_personnages.c.nombre, 0)
        )
        .outerjoin(
            comptes_personnages,
            comptes_personnages.c.joueur_id == Utilisateur.id
        )
        .where(Utilisateur.role == "coursier")
        .order_by(Utilisateur.is_active.desc(), Utilisateur.username)
    ).all()
    joueurs = [ligne[0] for ligne in lignes]
    nombre_personnages_par_joueur = {
        ligne[0].id: ligne[1]
        for ligne in lignes
    }
    return templates.TemplateResponse(
        request=request,
        name="admin_joueurs.html",
        context={
            "utilisateur": administrateur,
            "peut_preparer_itineraires": True,
            "joueurs": joueurs,
            "nombre_personnages_par_joueur": nombre_personnages_par_joueur
        }
    )


@router.get("/admin/joueurs/nouveau")
def formulaire_nouveau_joueur(
    request: Request,
    administrateur: Utilisateur = Depends(exiger_admin)
):
    return _rendre_formulaire_joueur(
        request,
        administrateur,
        mode="creation"
    )


@router.post("/admin/joueurs")
def creer_joueur(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    administrateur: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    username = username.strip()
    email = email.strip().lower()

    erreur = None
    status_code = 400
    if not username or not email:
        erreur = "Le login et l’adresse e-mail sont obligatoires."
    elif len(username) > 50:
        erreur = "Le login ne peut pas dépasser 50 caractères."
    elif len(email) > 255:
        erreur = "L’adresse e-mail ne peut pas dépasser 255 caractères."
    else:
        erreur = _erreur_unicite_joueur(db, username, email)
        if erreur:
            status_code = 409

    if erreur:
        return _rendre_formulaire_joueur(
            request,
            administrateur,
            mode="creation",
            username=username,
            email=email,
            erreur=erreur,
            status_code=status_code
        )

    joueur = Utilisateur(
        username=username,
        email=email,
        password_hash=hasher.hash("1234"),
        role="coursier",
        is_active=True
    )
    db.add(joueur)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return _rendre_formulaire_joueur(
            request,
            administrateur,
            mode="creation",
            username=username,
            email=email,
            erreur="Ce login ou cette adresse e-mail est déjà utilisé(e).",
            status_code=409
        )

    joueur_id = joueur.id
    return RedirectResponse(
        url=f"/admin/joueurs/{joueur_id}",
        status_code=303
    )


@router.get("/admin/joueurs/{joueur_id}/modifier")
def formulaire_modifier_joueur(
    request: Request,
    joueur_id: int,
    administrateur: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    joueur = _obtenir_joueur(db, joueur_id)
    return _rendre_formulaire_joueur(
        request,
        administrateur,
        mode="modification",
        username=joueur.username,
        email=joueur.email,
        joueur_id=joueur.id
    )


@router.post("/admin/joueurs/{joueur_id}/modifier")
def modifier_joueur(
    request: Request,
    joueur_id: int,
    username: str = Form(...),
    email: str = Form(...),
    administrateur: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    joueur = _obtenir_joueur(db, joueur_id)
    username = username.strip()
    email = email.strip().lower()

    erreur = None
    status_code = 400
    if not username or not email:
        erreur = "Le login et l’adresse e-mail sont obligatoires."
    elif len(username) > 50:
        erreur = "Le login ne peut pas dépasser 50 caractères."
    elif len(email) > 255:
        erreur = "L’adresse e-mail ne peut pas dépasser 255 caractères."
    else:
        erreur = _erreur_unicite_joueur(db, username, email, joueur.id)
        if erreur:
            status_code = 409

    if erreur:
        return _rendre_formulaire_joueur(
            request,
            administrateur,
            mode="modification",
            username=username,
            email=email,
            joueur_id=joueur.id,
            erreur=erreur,
            status_code=status_code
        )

    joueur_id = joueur.id
    joueur.username = username
    joueur.email = email
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return _rendre_formulaire_joueur(
            request,
            administrateur,
            mode="modification",
            username=username,
            email=email,
            joueur_id=joueur_id,
            erreur="Ce login ou cette adresse e-mail est déjà utilisé(e).",
            status_code=409
        )

    return RedirectResponse(
        url=f"/admin/joueurs/{joueur_id}",
        status_code=303
    )


@router.post("/admin/joueurs/{joueur_id}/desactiver")
def desactiver_joueur(
    joueur_id: int,
    _: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    joueur = _obtenir_joueur(db, joueur_id)
    joueur.is_active = False
    db.commit()
    return RedirectResponse(
        url=f"/admin/joueurs/{joueur.id}",
        status_code=303
    )


@router.post("/admin/joueurs/{joueur_id}/reactiver")
def reactiver_joueur(
    joueur_id: int,
    _: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    joueur = _obtenir_joueur(db, joueur_id)
    joueur.is_active = True
    db.commit()
    return RedirectResponse(
        url=f"/admin/joueurs/{joueur.id}",
        status_code=303
    )


@router.get("/admin/joueurs/{joueur_id}")
def fiche_joueur(
    request: Request,
    joueur_id: int,
    administrateur: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    joueur = _obtenir_joueur(db, joueur_id)
    personnages = db.scalars(
        select(Personnage)
        .options(selectinload(Personnage.grade))
        .where(Personnage.utilisateur_id == joueur.id)
        .order_by(Personnage.matricule, Personnage.id)
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="admin_joueur_detail.html",
        context={
            "utilisateur": administrateur,
            "peut_preparer_itineraires": True,
            "joueur": joueur,
            "personnages": personnages
        }
    )


@router.get("/admin/personnages")
def liste_personnages(
    request: Request,
    administrateur: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    personnages = db.scalars(
        select(Personnage)
        .options(
            selectinload(Personnage.compte),
            selectinload(Personnage.grade)
        )
        .order_by(Personnage.matricule, Personnage.id)
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="admin_personnages.html",
        context={
            "utilisateur": administrateur,
            "peut_preparer_itineraires": True,
            "personnages": personnages
        }
    )


@router.get("/admin/personnages/nouveau")
def formulaire_nouveau_personnage(
    request: Request,
    joueur_id: int | None = None,
    administrateur: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    if joueur_id is not None:
        _obtenir_joueur(db, joueur_id)
    return _rendre_formulaire_personnage(
        request,
        administrateur,
        db,
        mode="creation",
        joueur_id=joueur_id
    )


@router.post("/admin/personnages")
def creer_personnage(
    request: Request,
    matricule: str = Form(...),
    nom: str = Form(...),
    joueur_id: int = Form(...),
    grade_id: str = Form(""),
    administrateur: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    matricule = matricule.strip()
    nom = nom.strip()
    erreur = None
    status_code = 400
    if not matricule or not nom:
        erreur = "Le matricule et le nom sont obligatoires."
    elif len(matricule) > 50:
        erreur = "Le matricule ne peut pas dépasser 50 caractères."
    elif len(nom) > 100:
        erreur = "Le nom ne peut pas dépasser 100 caractères."
    else:
        erreur = _erreur_unicite_matricule(db, matricule)
        if erreur:
            status_code = 409

    grade_id_valide, erreur_grade = _obtenir_grade_optionnel(db, grade_id)
    if erreur is None and erreur_grade is not None:
        erreur = erreur_grade

    if erreur:
        return _rendre_formulaire_personnage(
            request,
            administrateur,
            db,
            mode="creation",
            matricule=matricule,
            nom=nom,
            joueur_id=joueur_id,
            grade_id=grade_id,
            erreur=erreur,
            status_code=status_code
        )

    _obtenir_joueur(db, joueur_id)
    personnage = Personnage(
        matricule=matricule,
        nom=nom,
        utilisateur_id=joueur_id,
        grade_id=grade_id_valide,
        cree_par_utilisateur_id=administrateur.id
    )
    db.add(personnage)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return _rendre_formulaire_personnage(
            request,
            administrateur,
            db,
            mode="creation",
            matricule=matricule,
            nom=nom,
            joueur_id=joueur_id,
            grade_id=grade_id,
            erreur="Le matricule est déjà utilisé ou une référence n’est plus valide.",
            status_code=409
        )

    return RedirectResponse(
        url=f"/admin/personnages/{personnage.id}",
        status_code=303
    )


@router.get("/admin/personnages/{personnage_id}/modifier")
def formulaire_modifier_personnage(
    request: Request,
    personnage_id: int,
    administrateur: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    personnage = _obtenir_personnage(db, personnage_id)
    return _rendre_formulaire_personnage(
        request,
        administrateur,
        db,
        mode="modification",
        matricule=personnage.matricule,
        nom=personnage.nom,
        joueur_id=personnage.utilisateur_id,
        grade_id=str(personnage.grade_id or ""),
        personnage_id=personnage.id
    )


@router.post("/admin/personnages/{personnage_id}/modifier")
def modifier_personnage(
    request: Request,
    personnage_id: int,
    matricule: str = Form(...),
    nom: str = Form(...),
    joueur_id: int = Form(...),
    grade_id: str = Form(""),
    administrateur: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    personnage = _obtenir_personnage(db, personnage_id)
    matricule = matricule.strip()
    nom = nom.strip()
    erreur = None
    status_code = 400
    if not matricule or not nom:
        erreur = "Le matricule et le nom sont obligatoires."
    elif len(matricule) > 50:
        erreur = "Le matricule ne peut pas dépasser 50 caractères."
    elif len(nom) > 100:
        erreur = "Le nom ne peut pas dépasser 100 caractères."
    else:
        erreur = _erreur_unicite_matricule(db, matricule, personnage.id)
        if erreur:
            status_code = 409

    grade_id_valide, erreur_grade = _obtenir_grade_optionnel(db, grade_id)
    if erreur is None and erreur_grade is not None:
        erreur = erreur_grade

    if erreur:
        return _rendre_formulaire_personnage(
            request,
            administrateur,
            db,
            mode="modification",
            matricule=matricule,
            nom=nom,
            joueur_id=joueur_id,
            grade_id=grade_id,
            personnage_id=personnage.id,
            erreur=erreur,
            status_code=status_code
        )

    _obtenir_joueur(db, joueur_id)
    personnage_id = personnage.id
    personnage.matricule = matricule
    personnage.nom = nom
    personnage.utilisateur_id = joueur_id
    personnage.grade_id = grade_id_valide
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return _rendre_formulaire_personnage(
            request,
            administrateur,
            db,
            mode="modification",
            matricule=matricule,
            nom=nom,
            joueur_id=joueur_id,
            grade_id=grade_id,
            personnage_id=personnage_id,
            erreur="Le matricule est déjà utilisé ou une référence n’est plus valide.",
            status_code=409
        )

    return RedirectResponse(
        url=f"/admin/personnages/{personnage_id}",
        status_code=303
    )


@router.get("/admin/personnages/{personnage_id}")
def fiche_personnage(
    request: Request,
    personnage_id: int,
    administrateur: Utilisateur = Depends(exiger_admin),
    db: Session = Depends(get_db)
):
    personnage = _obtenir_personnage(db, personnage_id)
    return templates.TemplateResponse(
        request=request,
        name="admin_personnage_detail.html",
        context={
            "utilisateur": administrateur,
            "peut_preparer_itineraires": True,
            "personnage": personnage,
            "libelle_grade": (
                personnage.grade.nom
                if personnage.grade is not None
                else "Prestataire externe"
            )
        }
    )


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
