from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import URL, create_engine, delete, func, insert, make_url, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import ArgumentError, SQLAlchemyError

from database.db_config import DatabaseConfigurationError, local_database_url
from database.models import Carte, CaseCarte


PREDEFINED_MAP_CODES = (
    "terres_neutres",
    "paradis",
    "enfer",
    "limbes",
)
ALLOWED_TERRAIN_CODES = frozenset(
    {
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
    }
)
MAX_REPORTED_ANOMALIES = 25


class SyncConfigurationError(Exception):
    pass


@dataclass(frozen=True)
class CarteInfo:
    id: int
    largeur: int
    hauteur: int


@dataclass
class ValidationReport:
    total: int = 0
    messages: list[str] = field(default_factory=list)

    def add(self, message: str) -> None:
        self.total += 1
        if len(self.messages) < MAX_REPORTED_ANOMALIES:
            self.messages.append(message)


def _normalize_postgres_url(raw_url: str, variable_name: str) -> URL:
    try:
        url = make_url(raw_url)
    except (ArgumentError, TypeError):
        raise SyncConfigurationError(
            f"La valeur de {variable_name} n'est pas une URL PostgreSQL valide."
        ) from None

    if url.drivername in ("postgres", "postgresql"):
        url = url.set(drivername="postgresql+psycopg")

    if not url.drivername.startswith("postgresql"):
        raise SyncConfigurationError(
            f"{variable_name} doit désigner une base PostgreSQL."
        )
    return url


def _local_url() -> URL:
    try:
        return local_database_url()
    except DatabaseConfigurationError as exc:
        raise SyncConfigurationError(str(exc)) from None


def _render_url() -> URL:
    database_url = os.getenv("RENDER_DATABASE_URL")
    if not database_url:
        raise SyncConfigurationError(
            "La variable RENDER_DATABASE_URL doit être définie."
        )
    return _normalize_postgres_url(database_url, "RENDER_DATABASE_URL")


def _url_identity(url: URL) -> tuple[str, int, str]:
    return (
        (url.host or "").lower().rstrip("."),
        url.port or 5432,
        url.database or "",
    )


def _database_identity(engine: Engine) -> tuple[str | None, int | None, str]:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT current_database(), "
                "inet_server_addr()::text, inet_server_port()"
            )
        ).one()
    return row[1], row[2], row[0]


def _same_database(
    local_url: URL,
    render_url: URL,
    local_identity: tuple[str | None, int | None, str],
    render_identity: tuple[str | None, int | None, str],
) -> bool:
    if _url_identity(local_url) == _url_identity(render_url):
        return True

    local_address, local_port, local_name = local_identity
    render_address, render_port, render_name = render_identity
    return (
        local_name == render_name
        and local_address is not None
        and render_address is not None
        and local_address == render_address
        and local_port == render_port
    )


def _read_cartes(connection) -> dict[str, CarteInfo]:
    rows = connection.execute(
        select(Carte.code, Carte.id, Carte.largeur, Carte.hauteur)
        .order_by(Carte.code)
    )
    return {
        row.code: CarteInfo(
            id=row.id,
            largeur=row.largeur,
            hauteur=row.hauteur,
        )
        for row in rows
    }


def _read_local_snapshot(
    engine: Engine,
) -> tuple[dict[str, CarteInfo], list[dict[str, object]]]:
    with engine.connect() as connection:
        cartes = _read_cartes(connection)
        rows = connection.execute(
            select(
                Carte.code.label("code"),
                Carte.largeur.label("largeur"),
                Carte.hauteur.label("hauteur"),
                CaseCarte.x.label("x"),
                CaseCarte.y.label("y"),
                CaseCarte.terrain_code.label("terrain_code"),
                CaseCarte.variant.label("variant"),
            )
            .select_from(CaseCarte)
            .outerjoin(Carte, CaseCarte.carte_id == Carte.id)
            .order_by(Carte.code, CaseCarte.y, CaseCarte.x)
        )
        cases = [dict(row._mapping) for row in rows]
    return cartes, cases


def _read_render_snapshot(
    engine: Engine,
) -> tuple[
    dict[str, CarteInfo],
    int,
    dict[str | None, int],
]:
    with engine.connect() as connection:
        cartes = _read_cartes(connection)
        case_count = connection.scalar(
            select(func.count()).select_from(CaseCarte)
        )
        distribution_rows = connection.execute(
            select(Carte.code, func.count(CaseCarte.id))
            .select_from(CaseCarte)
            .outerjoin(Carte, CaseCarte.carte_id == Carte.id)
            .group_by(Carte.code)
            .order_by(Carte.code)
        )
        distribution = {
            row[0]: row[1]
            for row in distribution_rows
        }
    return cartes, int(case_count or 0), distribution


def _validate_snapshot(
    local_cartes: dict[str, CarteInfo],
    render_cartes: dict[str, CarteInfo],
    cases: list[dict[str, object]],
) -> ValidationReport:
    report = ValidationReport()

    for label, cartes in (
        ("locale", local_cartes),
        ("Render", render_cartes),
    ):
        missing = sorted(set(PREDEFINED_MAP_CODES) - cartes.keys())
        if missing:
            report.add(
                f"Codes prédéfinis absents de la base {label} : "
                f"{', '.join(missing)}."
            )

    case_codes = {
        case["code"]
        for case in cases
        if isinstance(case["code"], str)
    }
    missing_render_codes = sorted(case_codes - render_cartes.keys())
    if missing_render_codes:
        report.add(
            "Cartes référencées par des cases locales mais absentes de Render : "
            f"{', '.join(missing_render_codes)}."
        )

    checked_dimensions: set[str] = set()
    for index, case in enumerate(cases, start=1):
        code = case["code"]
        if not isinstance(code, str):
            report.add(
                f"Case locale {index} : carte associée introuvable."
            )
            continue

        local_carte = local_cartes.get(code)
        render_carte = render_cartes.get(code)
        if local_carte is not None and render_carte is not None:
            if code not in checked_dimensions:
                checked_dimensions.add(code)
                if (
                    local_carte.largeur <= 0
                    or local_carte.hauteur <= 0
                    or render_carte.largeur <= 0
                    or render_carte.hauteur <= 0
                ):
                    report.add(
                        f"Dimensions invalides pour la carte {code}."
                    )
                if (
                    local_carte.largeur != render_carte.largeur
                    or local_carte.hauteur != render_carte.hauteur
                ):
                    report.add(
                        f"Dimensions différentes pour la carte {code} "
                        "entre la base locale et Render."
                    )

        x = case["x"]
        y = case["y"]
        for coordinate_name, coordinate in (("x", x), ("y", y)):
            if type(coordinate) is not int or coordinate < 0:
                report.add(
                    f"Case locale {index} : coordonnée {coordinate_name} "
                    "non entière ou négative."
                )

        if type(x) is int and type(y) is int:
            if local_carte is not None and (
                x >= local_carte.largeur or y >= local_carte.hauteur
            ):
                report.add(
                    f"Case locale {index} : coordonnées hors limites "
                    f"de la carte {code}."
                )
            if render_carte is not None and (
                x >= render_carte.largeur or y >= render_carte.hauteur
            ):
                report.add(
                    f"Case locale {index} : coordonnées hors limites "
                    f"de la carte {code} sur Render."
                )

        terrain_code = case["terrain_code"]
        if (
            not isinstance(terrain_code, str)
            or not terrain_code
            or len(terrain_code) > 40
        ):
            report.add(
                f"Case locale {index} : terrain_code vide, invalide "
                "ou supérieur à 40 caractères."
            )
        elif terrain_code not in ALLOWED_TERRAIN_CODES:
            report.add(
                f"Case locale {index} : code de terrain inconnu "
                f"({terrain_code})."
            )

        variant = case["variant"]
        if type(variant) is not int or not 1 <= variant <= 4:
            report.add(
                f"Case locale {index} : variant doit être un entier de 1 à 4."
            )

    return report


def _print_distribution(
    title: str,
    distribution: dict[str | None, int],
    cartes: dict[str, CarteInfo],
) -> None:
    print(title)
    for code in sorted(cartes):
        print(f"  {code} : {distribution.get(code, 0)}")
    if None in distribution:
        print(f"  carte inconnue : {distribution[None]}")


def _print_report(
    local_cartes: dict[str, CarteInfo],
    render_cartes: dict[str, CarteInfo],
    cases: list[dict[str, object]],
    render_case_count: int,
    render_distribution: dict[str | None, int],
    validation: ValidationReport,
) -> None:
    local_distribution = Counter(
        case["code"] if isinstance(case["code"], str) else None
        for case in cases
    )

    print("Bilan de synchronisation de cases_carte")
    print(f"Cases locales : {len(cases)}")
    print(f"Cases actuellement sur Render : {render_case_count}")
    print(f"Cases prévues pour le transfert : {len(cases)}")
    _print_distribution(
        "Répartition locale par carte :",
        dict(local_distribution),
        local_cartes,
    )
    _print_distribution(
        "Répartition actuelle sur Render :",
        render_distribution,
        render_cartes,
    )

    if validation.total:
        print(f"Anomalies détectées : {validation.total}")
        for message in validation.messages:
            print(f"  - {message}")
        if validation.total > len(validation.messages):
            print(
                "  - Certaines anomalies ne sont pas affichées "
                f"(maximum : {MAX_REPORTED_ANOMALIES})."
            )
    else:
        print("Anomalies détectées : aucune")


def _confirm_publication() -> bool:
    confirmation = "PUBLIER cases_carte"
    print(
        "\nCette opération remplacera toutes les cases_carte sur Render. "
        "Pour confirmer, saisissez exactement : "
        f"{confirmation}"
    )
    try:
        return input("> ").strip() == confirmation
    except EOFError:
        return False


def _publish(
    engine: Engine,
    local_cases: list[dict[str, object]],
    local_cartes: dict[str, CarteInfo],
    displayed_case_count: int,
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text("LOCK TABLE cases_carte IN SHARE ROW EXCLUSIVE MODE")
        )
        current_case_count = connection.scalar(
            select(func.count()).select_from(CaseCarte)
        )
        if int(current_case_count or 0) != displayed_case_count:
            raise SyncConfigurationError(
                "Le nombre de cases sur Render a changé depuis le bilan; "
                "relancez le script."
            )

        render_cartes = _read_cartes_for_share(connection)
        validation = _validate_snapshot(
            local_cartes,
            render_cartes,
            local_cases,
        )
        if validation.total:
            raise SyncConfigurationError(
                "Les validations Render ont échoué avant la suppression : "
                + " ".join(validation.messages)
            )

        connection.execute(delete(CaseCarte))
        payload = [
            {
                "carte_id": render_cartes[case["code"]].id,
                "x": case["x"],
                "y": case["y"],
                "terrain_code": case["terrain_code"],
                "variant": case["variant"],
            }
            for case in local_cases
        ]
        if payload:
            connection.execute(insert(CaseCarte.__table__), payload)


def _read_cartes_for_share(connection) -> dict[str, CarteInfo]:
    rows = connection.execute(
        select(Carte.code, Carte.id, Carte.largeur, Carte.hauteur)
        .order_by(Carte.code)
        .with_for_update(read=True)
    )
    return {
        row.code: CarteInfo(
            id=row.id,
            largeur=row.largeur,
            hauteur=row.hauteur,
        )
        for row in rows
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Synchronise cases_carte de la base locale vers Render. "
            "Par défaut, le script fonctionne en simulation."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="publier après validation et confirmation interactive",
    )
    args = parser.parse_args(argv)

    local_engine: Engine | None = None
    render_engine: Engine | None = None
    try:
        local_url = _local_url()
        render_url = _render_url()
        if _url_identity(local_url) == _url_identity(render_url):
            raise SyncConfigurationError(
                "La configuration locale et Render désigne la même base; "
                "opération refusée."
            )

        local_engine = create_engine(
            local_url,
            pool_pre_ping=True,
            hide_parameters=True,
        )
        render_engine = create_engine(
            render_url,
            pool_pre_ping=True,
            hide_parameters=True,
        )

        local_identity = _database_identity(local_engine)
        render_identity = _database_identity(render_engine)
        if _same_database(
            local_url,
            render_url,
            local_identity,
            render_identity,
        ):
            raise SyncConfigurationError(
                "Les connexions locale et Render aboutissent à la même base; "
                "opération refusée."
            )

        local_cartes, local_cases = _read_local_snapshot(local_engine)
        (
            render_cartes,
            render_case_count,
            render_distribution,
        ) = _read_render_snapshot(render_engine)
        validation = _validate_snapshot(
            local_cartes,
            render_cartes,
            local_cases,
        )
        _print_report(
            local_cartes,
            render_cartes,
            local_cases,
            render_case_count,
            render_distribution,
            validation,
        )

        if validation.total:
            print("Aucune écriture effectuée.")
            return 1

        if not args.apply:
            print("Simulation terminée : aucune écriture effectuée.")
            return 0

        if not _confirm_publication():
            print("Confirmation absente ou incorrecte; aucune écriture effectuée.")
            return 1

        _publish(
            render_engine,
            local_cases,
            local_cartes,
            render_case_count,
        )
        print("Synchronisation terminée; transaction validée.")
        return 0
    except SyncConfigurationError as exc:
        print(f"Opération refusée : {exc}", file=sys.stderr)
        return 1
    except SQLAlchemyError as exc:
        print(
            "Erreur PostgreSQL/SQLAlchemy "
            f"({type(exc).__name__}); aucune transaction n'a été validée. "
            "Les détails de connexion sont masqués.",
            file=sys.stderr,
        )
        return 1
    finally:
        if local_engine is not None:
            local_engine.dispose()
        if render_engine is not None:
            render_engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
