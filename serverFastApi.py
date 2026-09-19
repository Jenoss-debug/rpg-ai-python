from fastapi import FastAPI

serveur_rpg = FastAPI()

@serveur_rpg.get("/")
def accueil():

    return {
        "message": "Bonjour Thomas !"
    }
