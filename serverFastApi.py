from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

serveur_rpg = FastAPI()

# Gestion des fichiers CSS et JavaScript
serveur_rpg.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

# Emplacement des pages HTML
templates = Jinja2Templates(directory="templates")


@serveur_rpg.get("/")
def accueil(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )