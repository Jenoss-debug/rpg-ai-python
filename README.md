# Médiéval Relais

Application Python avec FastAPI, SQLAlchemy, PostgreSQL et Alembic.

## Tester les espaces par rôle

Les pages `/admin` et `/coursier` exigent une session valide et le rôle
correspondant côté serveur. Les liens de navigation sont également adaptés au
rôle, mais ne remplacent pas ces contrôles.

Pour créer un compte coursier de test sur la base configurée par
`DATABASE_URL` (ou les variables locales `DB_*`), lancez :

```powershell
python -m database.seed_demo
```

Le script demande un identifiant, une adresse e-mail et un mot de passe
(12 caractères minimum), crée le compte coursier si nécessaire, puis ajoute
trois livraisons de démonstration qui lui sont attribuées. Les identifiants ne
sont pas enregistrés dans le code.

La page `/preparation-itineraires` est accessible aux administrateurs et aux
coursiers possédant un personnage avec un grade. Elle affiche une carte
hexagonale finie de 100 × 100 cases, déplaçable et zoomable à la souris. Le
survol et la sélection d’une case sont disponibles ; les coordonnées peuvent
être affichées à partir d’un niveau de zoom configurable dans le JavaScript.
Aucun calcul d’itinéraire ni persistance de la carte n’est encore effectué.
