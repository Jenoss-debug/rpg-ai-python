import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from routers.admin import router as admin_router
from routers.auth import router as auth_router
from routers.pages import router as pages_router
from routers.private import router as private_router


# Application
serveur_rpg = FastAPI()

# Clé secrète obligatoire pour signer les sessions
SESSION_SECRET = os.getenv("SESSION_SECRET")
if not SESSION_SECRET:
    raise RuntimeError("La variable SESSION_SECRET n'est pas définie.")

# Gestion des sessions
serveur_rpg.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="rpg_session",
    max_age=8 * 60 * 60,  # 8 heures
    same_site="lax",
    https_only=os.getenv("APP_ENV") == "production"
)

# Fichiers statiques et templates
serveur_rpg.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

serveur_rpg.include_router(pages_router)
serveur_rpg.include_router(auth_router)
serveur_rpg.include_router(private_router)
serveur_rpg.include_router(admin_router)