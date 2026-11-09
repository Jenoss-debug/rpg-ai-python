
from getpass import getpass

from argon2 import PasswordHasher
from sqlalchemy import select

from database.connexion import SessionLocal
from database.models import Utilisateur, Livraison


LIVRAISONS_DEMO = [
    {
        "reference": "DEMO-001",
        "nom_client": "Auberge du Dragon",
        "destinataire": "Auberge du Dragon",
        "secteur_depart": "Palaiseau",
        "secteur_arrivee": "Massy",
        "coord_depart_x": 10,
        "coord_depart_y": 12,
        "coord_arrivee_x": 14,
        "coord_arrivee_y": 12,
        "description": "Livraison de 3 potions de soin",
        "recompense_po": 25,
        "statut": "a_preparer",
    },
    {
        "reference": "DEMO-002",
        "nom_client": "Marchand Gildas",
        "destinataire": "Marchand Gildas",
        "secteur_depart": "Massy",
        "secteur_arrivee": "Antony",
        "coord_depart_x": 14,
        "coord_depart_y": 12,
        "coord_arrivee_x": 17,
        "coord_arrivee_y": 15,
        "description": "Livraison de 2 épées en acier",
        "recompense_po": 40,
        "statut": "en_cours",
    },
    {
        "reference": "DEMO-003",
        "nom_client": "Guilde des Artisans",
        "destinataire": "Guilde des Artisans",
        "secteur_depart": "Antony",
        "secteur_arrivee": "Versailles",
        "coord_depart_x": 17,
        "coord_depart_y": 15,
        "coord_arrivee_x": 23,
        "coord_arrivee_y": 19,
        "description": "Livraison de matériaux de construction",
        "recompense_po": 60,
        "statut": "livree",
    },
]

def creer_donnees_demo():
    hasher = PasswordHasher()

    with SessionLocal() as db:

        print("\n--- Création du coursier de démonstration ---")

        username = input("Identifiant du coursier : ").strip()
        email = input("Adresse email : ").strip().lower()

        if not username or not email:
            print("Identifiant et email obligatoires.")
            return

        utilisateur_username = db.scalar(
            select(Utilisateur).where(
                Utilisateur.username == username
            )
        )

        utilisateur_email = db.scalar(
            select(Utilisateur).where(
                Utilisateur.email == email
            )
        )

        if (
            utilisateur_username is not None
            and utilisateur_email is not None
            and utilisateur_username.id != utilisateur_email.id
        ):
            print("Cet identifiant et cet email appartiennent à deux comptes différents.")
            return

        coursier = utilisateur_username or utilisateur_email

        if coursier is not None:
            if coursier.role != "coursier":
                print("Ce compte n'est pas un coursier. Opération annulée.")
                return

            print(f"Compte coursier existant : {coursier.username}")

        else:
            password = getpass("Mot de passe du coursier : ")
            confirmation = getpass("Confirmer le mot de passe : ")

            if len(password) < 12:
                print("Le mot de passe doit contenir au moins 12 caractères.")
                return

            if password != confirmation:
                print("Les mots de passe ne correspondent pas.")
                return

            coursier = Utilisateur(
                username=username,
                email=email,
                password_hash=hasher.hash(password),
                role="coursier",
                is_active=True
            )

            db.add(coursier)
            db.flush()

            print("Compte coursier créé.")

        print("\n--- Création des livraisons ---")

        for donnees in LIVRAISONS_DEMO:

            livraison_existante = db.scalar(
                select(Livraison).where(
                    Livraison.reference == donnees["reference"]
                )
            )

            if livraison_existante is not None:
                print(f"{donnees['reference']} existe déjà : ignorée.")
                continue

            livraison = Livraison(
                **donnees,
                coursier_id=coursier.id
            )

            db.add(livraison)
            print(f"{donnees['reference']} ajoutée.")

        db.commit()

        print("\nDonnées de démonstration créées avec succès !")
        print(f"Coursier : {coursier.username}")


if __name__ == "__main__":
    creer_donnees_demo()
