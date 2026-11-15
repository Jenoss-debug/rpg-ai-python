import os

from sqlalchemy import URL, make_url
from sqlalchemy.exc import ArgumentError


class DatabaseConfigurationError(RuntimeError):
    pass


def _postgres_url(raw_url: str, variable_name: str) -> URL:
    try:
        url = make_url(raw_url)
    except (ArgumentError, TypeError):
        raise DatabaseConfigurationError(
            f"La valeur de {variable_name} n'est pas une URL PostgreSQL valide."
        ) from None

    if url.drivername in ("postgres", "postgresql"):
        url = url.set(drivername="postgresql+psycopg")

    if not url.drivername.startswith("postgresql"):
        raise DatabaseConfigurationError(
            f"{variable_name} doit désigner une base PostgreSQL."
        )
    return url


def local_database_url() -> URL:
    password = os.getenv("DB_PASSWORD")
    if not password:
        raise DatabaseConfigurationError(
            "La variable DB_PASSWORD doit être définie pour la base locale."
        )

    try:
        port = int(os.getenv("DB_PORT", "5432"))
    except ValueError:
        raise DatabaseConfigurationError(
            "DB_PORT doit être un numéro de port valide."
        ) from None

    return URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("DB_USER", "postgres"),
        password=password,
        host=os.getenv("DB_HOST", "localhost"),
        port=port,
        database=os.getenv("DB_NAME", "rpg_ai_db"),
    )


def app_database_url() -> URL:
    environment = os.getenv("APP_ENV", "local").strip().lower()
    if environment == "production":
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise DatabaseConfigurationError(
                "La variable DATABASE_URL doit être définie en production."
            )
        return _postgres_url(database_url, "DATABASE_URL")

    if environment != "local":
        raise DatabaseConfigurationError(
            "APP_ENV doit être 'local' ou 'production'."
        )

    return local_database_url()


def migration_database_url() -> URL:
    render_url = os.getenv("RENDER_DATABASE_URL")
    if render_url:
        return _postgres_url(render_url, "RENDER_DATABASE_URL")
    return local_database_url()
