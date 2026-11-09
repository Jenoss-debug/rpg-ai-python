from database.base import Base
from database.connexion import engine

# Import des modèles pour les enregistrer dans Base.metadata
from database import models


def initialiser_bdd():

    Base.metadata.create_all(bind=engine)

    print("Initialisation de la base terminée !")


if __name__ == "__main__":
    initialiser_bdd()