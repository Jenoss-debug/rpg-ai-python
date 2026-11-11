from pathlib import Path

from alembic import command
from alembic.config import Config


def initialiser_bdd():
    config_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    command.upgrade(Config(str(config_path)), "head")

    print("Base de données mise à niveau jusqu'à la dernière révision !")


if __name__ == "__main__":
    initialiser_bdd()