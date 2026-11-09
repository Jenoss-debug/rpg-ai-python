
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from argon2 import PasswordHasher

from database.connexion import SessionLocal
from database.models import Utilisateur


def creer_administrateur():

    hasher = PasswordHasher()

    with SessionLocal() as db:

        # Vérifier qu'un administrateur n'existe pas déjà
        admin_existant = db.scalar(
            select(Utilisateur).where(
                Utilisateur.role == "admin"
            )
        )

        if admin_existant:
            print("Un administrateur existe déjà.")
            return

        print("\n--- Création du compte administrateur ---")

        username = input("Identifiant : ").strip()
        email = input("Adresse email : ").strip().lower()

        if not username or not email:
            print("Identifiant et email obligatoires.")
            return

        # Vérifier les doublons
        utilisateur_existant = db.scalar(
            select(Utilisateur).where(
                (Utilisateur.username == username)
                | (Utilisateur.email == email)
            )
        )

        if utilisateur_existant:
            print("Cet identifiant ou cet email existe déjà.")
            return

        password = getpass("Mot de passe : ")
        confirmation = getpass("Confirmer le mot de passe : ")

        if len(password) < 12:
            print("Le mot de passe doit contenir au moins 12 caractères.")
            return

        if password != confirmation:
            print("Les mots de passe ne correspondent pas.")
            return

        # Hachage du mot de passe
        password_hash = hasher.hash(password)

        administrateur = Utilisateur(
            username=username,
            email=email,
            password_hash=password_hash,
            role="admin",
            is_active=True
        )

        try:
            db.add(administrateur)
            db.commit()

            print("\nAdministrateur créé avec succès !")
            print(f"Identifiant : {username}")

        except IntegrityError:
            db.rollback()
            print("Erreur : identifiant ou email déjà utilisé.")


if __name__ == "__main__":
    creer_administrateur()
