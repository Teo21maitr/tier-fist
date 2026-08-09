# Mettre Tier Fist en production sur Railway

Tutoriel pas à pas, depuis un dépôt local qui n'est pas encore sur GitHub.

Compte le temps : environ **30 minutes** la première fois.

---

## Vue d'ensemble

À la fin, tu auras sur Railway un **projet** contenant trois choses :

```text
Projet « tier-fist »
├── Postgres          la base de données (fournit DATABASE_URL)
├── tier-fist (web)   l'application, construite depuis le Dockerfile
└── Volume            disque persistant monté sur /data/media (les images)
```

Le service web est relié à la branche `main` de GitHub : **chaque push sur
`main` déclenche un déploiement**, et les migrations Django s'exécutent
automatiquement au démarrage du conteneur.

---

## Étape 1 — Mettre le code sur GitHub

Le dépôt local existe déjà, avec deux branches (`develop` et `main`) et un
commit. Il n'a simplement pas encore de dépôt distant.

### 1.1 Créer le dépôt sur GitHub

Va sur **https://github.com/new** et remplis :

- **Repository name** : `tier-fist`
- **Private** (les Tier Lists sont privées, autant que le code le soit aussi)
- **Ne coche rien d'autre** : ni README, ni .gitignore, ni licence. Le dépôt
  doit rester vide, sinon le premier `push` sera refusé.

Clique sur **Create repository**.

### 1.2 Relier le dépôt local et pousser

GitHub affiche alors une URL de la forme
`https://github.com/<ton-pseudo>/tier-fist.git`. Reprends-la ci-dessous.

```bash
cd /Users/teomaitrot/Documents/projet-perso/tier-fist
git remote add origin https://github.com/<ton-pseudo>/tier-fist.git
git push -u origin develop
git push -u origin main
```

Si Git demande un mot de passe, ce n'est pas celui de ton compte GitHub mais un
**personal access token** : https://github.com/settings/tokens → *Generate new
token (classic)* → coche la portée `repo`. Colle le token en guise de mot de
passe.

### 1.3 Vérifier

```bash
git remote -v
git ls-remote --heads origin
```

Tu dois voir `develop` et `main`. Vérifie aussi sur GitHub que le fichier
`.env` **n'apparaît pas** : il est ignoré par `.gitignore`, et il contient ta
clé secrète.

---

## Étape 2 — Créer le projet Railway

1. Va sur **https://railway.app** et connecte-toi (« Login with GitHub » est le
   plus simple, et autorisera l'accès au dépôt à l'étape suivante).
2. Clique sur **New Project**.
3. Choisis **Deploy from GitHub repo**.
4. Si Railway ne voit pas ton dépôt, clique sur **Configure GitHub App** et
   donne-lui accès à `tier-fist` (tu peux n'autoriser que ce dépôt).
5. Sélectionne `tier-fist`.

Railway crée le service et lance un premier build. **Il va échouer** : la base
de données n'existe pas encore. C'est normal, on la crée à l'étape suivante.

### 2.1 Déployer depuis `main`, pas depuis `develop`

Ouvre le service web → onglet **Settings** → section **Source** :

- **Branch** : `main`

C'est la branche de production. Le développement continue sur `develop`.

---

## Étape 3 — Ajouter PostgreSQL

Dans le canevas du projet :

1. Clique sur **+ Create** (ou fais un clic droit sur le fond) → **Database**
   → **Add PostgreSQL**.
2. Railway crée un service `Postgres` et expose automatiquement une variable
   `DATABASE_URL`.

### 3.1 Brancher la base sur l'application

Ouvre le service **web** → onglet **Variables** → **+ New Variable** →
**Add Reference** → choisis `Postgres` puis `DATABASE_URL`.

Tu dois obtenir une ligne du type :

```text
DATABASE_URL = ${{Postgres.DATABASE_URL}}
```

C'est une **référence**, pas une copie : si Railway fait tourner les
identifiants de la base, l'application suit automatiquement.

---

## Étape 4 — Ajouter le volume persistant pour les images

Sans cette étape, les images uploadées disparaîtraient à chaque redéploiement.

1. Ouvre le service **web**.
2. Onglet **Settings** → section **Volumes** → **+ Add Volume** (ou clic droit
   sur le service → **Attach Volume**).
3. **Mount path** : `/data/media`

Exactement ce chemin : le `Dockerfile` positionne déjà `MEDIA_ROOT=/data/media`.

---

## Étape 5 — Renseigner les variables d'environnement

Toujours dans le service **web**, onglet **Variables**. Ajoute les lignes
suivantes (le bouton **Raw Editor** permet de tout coller d'un coup).

### 5.1 Générer la clé secrète

Sur ta machine :

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

Copie le résultat. **Ne réutilise pas** celui de ton `.env` local.

### 5.2 Les variables

```bash
DJANGO_SECRET_KEY=colle-ici-la-clé-générée
DJANGO_DEBUG=False
MEDIA_ROOT=/data/media
MAX_UPLOAD_IMAGE_SIZE=5242880
```

`DATABASE_URL` est déjà là depuis l'étape 3.

Tu n'as **pas** besoin de renseigner `ALLOWED_HOSTS` ni
`CSRF_TRUSTED_ORIGINS` : l'application lit `RAILWAY_PUBLIC_DOMAIN`, que Railway
injecte tout seul, et en déduit les deux.

> Si tu branches plus tard un domaine personnalisé, ajoute-le explicitement :
> `ALLOWED_HOSTS=tierfist.fr` et `CSRF_TRUSTED_ORIGINS=https://tierfist.fr`.

---

## Étape 6 — Exposer l'application sur Internet

Service **web** → **Settings** → section **Networking** → **Generate Domain**.

Railway demande un **target port**. **Laisse-le détecter tout seul**, ou saisis
**8080**.

> C'est le piège le plus courant. Le conteneur écoute sur `$PORT`, une variable
> que Railway injecte et dont la valeur par défaut est **8080** — pas 8000. Si
> le domaine pointe vers un autre port, l'application démarre normalement, la
> sonde passe au vert, et pourtant toutes les pages répondent **502 Bad
> Gateway** : le proxy frappe une porte où personne n'écoute.
>
> Pour vérifier la valeur réelle, cherche cette ligne dans les *Deploy Logs* :
> `[INFO] Listening at: http://0.0.0.0:8080`. Le target port du domaine doit
> être ce nombre.

Tu obtiens une URL du type `tier-fist-production.up.railway.app`.

---

## Étape 7 — Déployer

Si le déploiement ne repart pas tout seul : service **web** → menu **⋮** →
**Redeploy**.

Suis l'onglet **Deploy Logs**. Le déroulé attendu :

```text
1. Build du frontend (npm ci puis npm run build)
2. Installation des dépendances Python
3. collectstatic
4. Démarrage : migrations Django, puis gunicorn
5. Healthcheck sur /healthz → succès → mise en ligne
```

Le premier build prend 3 à 5 minutes.

### Vérifier

```bash
curl https://<ton-domaine>.up.railway.app/healthz
```

Réponse attendue :

```json
{"status": "ok"}
```

Cette sonde vérifie aussi que la base répond : si elle échoue, le déploiement
est refusé plutôt que mis en ligne cassé.

Ouvre ensuite l'URL dans un navigateur : tu dois voir l'écran de connexion et
Laurent Baffist.

---

## Étape 8 — Créer ton compte administrateur

Il n'existe encore aucun compte en production. Comme l'inscription exige une
validation par un administrateur, il faut créer le premier à la main.

```bash
railway login
railway link          # choisis le projet tier-fist, puis le service web
railway ssh
```

Une fois dans le conteneur :

```bash
cd /app/backend
python manage.py createsuperuser
```

Choisis un pseudo et un mot de passe solide, puis `exit`.

> **Si `railway ssh` n'est pas disponible sur ton offre**, passe par l'URL
> publique de la base : service `Postgres` → **Variables** →
> `DATABASE_PUBLIC_URL`. Puis, depuis ta machine :
>
> ```bash
> cd /Users/teomaitrot/Documents/projet-perso/tier-fist/backend
> DATABASE_URL='<colle DATABASE_PUBLIC_URL ici>' .venv/bin/python manage.py createsuperuser
> ```

---

## Étape 9 — Recette en production

Connecte-toi sur `https://<ton-domaine>/admin/` avec ce compte, puis déroule :

1. Depuis l'application, crée un compte via **Créer un compte**.
2. Vérifie qu'il **ne peut pas** se connecter (message « compte en attente »).
3. Dans l'admin, **Utilisateurs** → sélectionne le compte → action
   **Accepter les comptes sélectionnés**.
4. Connecte-toi avec, crée une Tier List, note le code d'invitation.
5. Ajoute un item **avec une image uploadée** : c'est ce qui valide le volume.
6. Redéploie (**⋮** → **Redeploy**) et vérifie qu'après redémarrage
   l'image est **toujours là** et le compte **toujours présent**. C'est la
   preuve que rien n'est perdu au redéploiement.

---

## Le cycle de travail ensuite

```bash
# on développe sur develop
git checkout develop
# ... modifications ...
git add -A && git commit -m "..."
git push origin develop

# quand c'est prêt pour la production
git checkout main
git merge develop
git push origin main     # ← déclenche le déploiement Railway
git checkout develop
```

---

## Dépannage

| Symptôme dans les logs | Cause | Correctif |
|---|---|---|
| `Healthcheck failed` | La base n'est pas branchée | Vérifie la référence `DATABASE_URL` (étape 3.1) |
| `DisallowedHost` avec un domaine personnalisé | Domaine absent de la configuration | Ajoute `ALLOWED_HOSTS` et `CSRF_TRUSTED_ORIGINS` |
| `CSRF verification failed` à la connexion | Origine non déclarée | `CSRF_TRUSTED_ORIGINS=https://ton-domaine` (avec `https://`) |
| **502 Bad Gateway** alors que les logs montrent `Listening at: http://0.0.0.0:8080` | Le target port du domaine ne correspond pas à `$PORT` | Settings → Networking → règle le target port sur **8080** (étape 6) |
| Page blanche, 404 sur les fichiers `.js` | `collectstatic` a échoué au build | Regarde les *Build Logs* ; le build frontend a dû échouer avant |
| Les images disparaissent après un redéploiement | Volume absent ou mal monté | Point de montage exactement `/data/media` (étape 4) |
| `relation ... does not exist` | Migrations non passées | Regarde les *Deploy Logs* : `migrate` tourne avant gunicorn |

Pour lire les logs en direct depuis ton terminal :

```bash
railway logs
```

---

## Coûts

Le plan gratuit de Railway (« Trial ») suffit pour tester mais s'épuise. Le
plan **Hobby** (~5 $/mois de crédits) couvre confortablement une application de
cette taille : un service web, une base Postgres et un petit volume.

Pense à surveiller l'onglet **Usage** du projet.
