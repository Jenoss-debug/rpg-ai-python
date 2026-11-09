from sqlalchemy import text
from database.connexion import engine

with engine.connect() as connexion:
    resultat = connexion.execute(
        text("SELECT current_database(), current_user")
    )

    nom_bdd, utilisateur = resultat.one()

    print(f"Connexion réussie !")
    print(f"Base de données : {nom_bdd}")
    print(f"Utilisateur : {utilisateur}")
