# Tier Fist

Des Tier Lists collaboratives dont le classement n'est pas bricolé à la main :
les joueurs répondent à six affirmations par item, et un algorithme produit le
classement collectif. Chacun dispose ensuite d'un unique joker pour déplacer un
item.

Mascotte officielle : **Laurent Baffist**, petit robot sarcastique mais jamais
méchant.

L'interface est exclusivement en français.

---

## Démarrage rapide

Prérequis : Python 3.10+, Node 20+, Docker (pour PostgreSQL).

```bash
git clone <url> tier-fist && cd tier-fist
cp .env.example .env            # puis renseigne DJANGO_SECRET_KEY
docker compose up -d postgres   # PostgreSQL sur le port 5433
```

Backend :

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

Frontend, dans un autre terminal :

```bash
cd frontend && npm install && npm run dev
```

L'application est sur http://localhost:5173, l'admin Django sur
http://localhost:8000/admin/.

### Jeu de données de démonstration

```bash
cd backend && .venv/bin/python manage.py seed_demo --reset
```

Crée les comptes `teo`, `laura`, `paul` (mot de passe `MotDePasse!42`) et quatre
Tier Lists, une par statut du cycle de vie. C'est aussi le prérequis des tests
E2E.

---

## Tests

```bash
cd backend && .venv/bin/python -m pytest        # tests métier, API, permissions
cd frontend && npm test                          # composants et logique critique
cd frontend && npm run test:e2e                  # parcours complets (Playwright)
```

Les tests E2E supposent le backend lancé et `seed_demo` exécuté. Playwright
démarre lui-même le serveur Vite.

Le fichier `backend/tests/test_ranking_algorithm.py` est la **spécification
exécutable** de l'algorithme de classement : les cas de la spec y sont écrits
avec leur résultat attendu explicite.

---

## Architecture

```text
backend/
  config/       réglages Django, URLs, gestion d'erreurs API
  accounts/     utilisateur personnalisé, inscription, validation admin
  tierlists/    Tier Lists, items, questions, réponses, classement, jokers
    services/   règles métier isolées des vues
      ranking.py     algorithme de classement (fonction pure + pipeline)
      lifecycle.py   finalisation, réponses, transitions de statut
      jokers.py      phase joker, verrouillage, fin de partie
      structure.py   coefficients et conditions de finalisation
  tests/        tests métier, API et permissions
frontend/
  src/api/        client HTTP (cookies + CSRF) et hooks TanStack Query
  src/components/ mascotte, grille de Tier List, briques d'interface
  src/features/   auth, items, questions, questionnaire, résultats, thème
  src/pages/      un écran par route
  e2e/            parcours Playwright
```

Le backend reste la source de vérité : aucune règle métier critique ne vit
uniquement dans le frontend.

---

## Cycle de vie d'une Tier List

```text
DRAFT ──finalisation (créateur)──▶ ANSWERING ──dernier participant──▶ JOKER ──tous les jokers joués──▶ COMPLETED
```

- **DRAFT** — tous les participants ajoutent items et questions, renomment les
  rangs. Le code d'invitation permet de rejoindre.
- **ANSWERING** — structure figée, chacun répond item par item. Les réponses des
  autres restent invisibles ; seule leur progression est partagée.
- **JOKER** — le classement est calculé une fois pour toutes. Les jokers sont
  joués dans l'ordre inverse de complétion du questionnaire.
- **COMPLETED** — le classement courant devient définitif.

---

## Déploiement Railway

Le service web est construit avec le `Dockerfile` à la racine : il compile le
frontend, puis Django sert l'API **et** le SPA depuis la même origine — les
cookies de session fonctionnent sans configuration CORS particulière.

À provisionner sur Railway :

1. un service web relié à la branche `main` ;
2. une base **PostgreSQL** Railway (fournit `DATABASE_URL`) ;
3. un **volume persistant** monté sur `/data/media` pour les images uploadées.

Variables d'environnement :

| Variable                | Rôle                                              |
| ----------------------- | ------------------------------------------------- |
| `DJANGO_SECRET_KEY`     | obligatoire, jamais dans Git                      |
| `DJANGO_DEBUG`          | `False` en production                             |
| `DATABASE_URL`          | fourni par Railway                                |
| `ALLOWED_HOSTS`         | domaines autorisés                                |
| `CSRF_TRUSTED_ORIGINS`  | origines HTTPS du domaine                         |
| `MEDIA_ROOT`            | `/data/media` (volume persistant)                 |
| `MAX_UPLOAD_IMAGE_SIZE` | limite technique d'upload, en octets              |

`RAILWAY_PUBLIC_DOMAIN` est pris en compte automatiquement pour `ALLOWED_HOSTS`
et `CSRF_TRUSTED_ORIGINS`.

Les migrations sont exécutées au démarrage du conteneur. Un redéploiement
n'efface ni les données PostgreSQL ni les images du volume.

La sonde de santé `/healthz` vérifie que l'application répond **et** que la base
est joignable : un déploiement mal configuré est refusé plutôt que mis en ligne.

Marche à suivre détaillée : [`docs/DEPLOIEMENT_RAILWAY.md`](docs/DEPLOIEMENT_RAILWAY.md).

### Branches

- `develop` — développement ;
- `main` — production, reliée au déploiement Railway.

---

## Images

Formats acceptés à l'upload : **JPEG, PNG, GIF, WebP et HEIC**.

C'est le contenu réel du fichier qui décide, jamais son extension ni le
`Content-Type` annoncé : le fichier est décodé par Pillow, et le nom de stockage
est toujours regénéré côté serveur (spec §51).

Les photos **HEIC** (format par défaut des iPhone) sont acceptées puis
**converties en JPEG**, car Chrome et Firefox ne savent pas les afficher.
L'orientation EXIF est appliquée à la conversion, sans quoi les photos prises en
portrait apparaîtraient couchées.

La taille maximale est une limite **technique** anti-déni de service, réglable
via `MAX_UPLOAD_IMAGE_SIZE` (5 Mo par défaut). Ce n'est pas une règle métier.

Une image peut aussi être fournie par **URL distante**, sans téléchargement local.
Si les deux sont renseignées, l'upload prime.

---

## Comptes et validation

L'inscription ne demande qu'un pseudo et un mot de passe : aucune adresse email.
Un compte est créé en statut `PENDING` et ne peut pas se connecter tant qu'un
administrateur ne l'a pas accepté depuis le Django Admin (action « Accepter les
comptes sélectionnés »). Refuser un compte le supprime.

Il n'existe pas de récupération de mot de passe par email : un administrateur le
réinitialise depuis l'admin.

---

## Documentation complémentaire

- [`docs/DEPLOIEMENT_RAILWAY.md`](docs/DEPLOIEMENT_RAILWAY.md) — tutoriel pas à
  pas pour mettre l'application en production.
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — décisions techniques prises face aux
  points laissés ouverts par la spécification.
