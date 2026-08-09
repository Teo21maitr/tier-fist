# Décisions techniques

La spécification fonctionnelle fait autorité. Ce document consigne les choix
d'implémentation là où elle laissait explicitement la main, conformément à sa
règle §69.9 (« mettre à jour la documentation si une décision technique
importante est prise »).

---

## 1. L'état du joker vit sur `JokerAction`, pas sur le participant

**Spec concernée :** §48.3 et §48.9.

Le modèle recommandé plaçait un `joker_status` sur `TierListParticipant` *et* un
`status` sur `JokerAction`. Deux copies du même état finissent toujours par
diverger.

**Décision :** `TierListParticipant` ne conserve que `joker_order` (la position
dans la file). L'état `PENDING / USED / SKIPPED / FORCED_SKIP` vit uniquement sur
`JokerAction`, en relation un-à-un avec le participant, créée à l'entrée en phase
`JOKER`.

Aucun comportement métier n'est modifié : « le joueur a-t-il joué son joker ? »
se lit sur `JokerAction.status`.

---

## 2. Les ex æquo sont détectés sur des entiers exacts, pas sur des décimaux arrondis

**Spec concernée :** §25, §27.3, §27.5, §30.

Le score collectif vaut `Σ(réponse × coefficient) / (14 × N)`. C'est un
rationnel dont le dénominateur est identique pour tous les items d'une même
partie. Comparer les scores revient donc exactement à comparer leurs
**numérateurs entiers**.

**Décision :** le classement trie et détecte les égalités sur ces entiers. Le
`Decimal` n'intervient que pour la restitution (stocké à 10 décimales, affiché à
2). Aucune décision de rang ne dépend d'un arrondi, ce qui rend la règle « une
égalité n'est jamais cassée » exacte par construction.

La fonction `assign_ranks` reste générique : elle accepte aussi bien des entiers
que des `Decimal`, ce qui permet aux tests de la spécification d'être écrits
directement avec les valeurs décimales de la spec.

---

## 3. Frontières de rang : positions cumulées puis repoussées hors des ex æquo

**Spec concernée :** §27.2 à §27.5.

Les tailles cibles `[S, A, B, C, D]` sont calculées une fois : `S = max(1,
ceil(total × 10 %))`, puis le reste est réparti sur quatre rangs avec le
surplus attribué aux rangs les plus élevés.

Ces tailles donnent quatre **positions de coupe cumulées**. Chaque coupe est
ensuite repoussée vers l'avant tant qu'elle sépare deux items de score
identique, et reste monotone.

Conséquence, conforme à §27.5 : un rang peut déborder, et le rang suivant en
contient mécaniquement moins — jusqu'à être vide. Le cas extrême de §30 (tous les
scores égaux) en découle naturellement : tout atterrit en S.

---

## 4. Priorité de l'image d'un item : l'upload l'emporte

**Spec concernée :** §14.2, §48.4 (« définir une règle claire de priorité »).

**Décision :** `uploaded_image` prime sur `external_image_url`. Fournir un
fichier efface l'URL distante, et inversement — un item ne conserve jamais les
deux sources. Sans image, l'interface affiche le placeholder Laurent Baffist.

Les URLs distantes sont conservées telles quelles, sans téléchargement local
(§14.3).

---

## 5. Uploads : validation du contenu et nom généré côté serveur

**Spec concernée :** §14.2, §51.

- Le contenu est ouvert et vérifié par Pillow : ni l'extension ni le
  `Content-Type` annoncés ne sont crus.
- Formats acceptés : JPEG, PNG, GIF, WebP.
- Le nom de fichier est régénéré (`uuid4` + extension déduite du format réel),
  ce qui neutralise le path traversal.
- `MAX_UPLOAD_IMAGE_SIZE` (5 Mo par défaut) est une limite **technique**
  configurable, jamais présentée comme une règle métier.

---

## 6. Un non-participant reçoit 404, pas 403

**Spec concernée :** §10, §51 (« aucune Tier List privée exposée par simple
incrément d'ID »).

Toutes les requêtes sont filtrées par participation. Répondre 403 confirmerait
l'existence de la ressource ; l'API répond donc **404** à un non-participant,
exactement comme pour un identifiant inexistant.

---

## 7. Ordre des items : seed persistante par participant

**Spec concernée :** §17.

Chaque `TierListParticipant` reçoit à sa création une `answer_order_seed`
aléatoire. À la finalisation, l'ordre des items est tiré avec
`random.Random(seed)` et matérialisé dans `ParticipantItemProgress.display_order`.

L'ordre est donc indépendant d'un participant à l'autre, et strictement stable
d'un rafraîchissement à l'autre.

---

## 8. Concurrence : verrou sur la Tier List

**Spec concernée :** §52.

Les opérations sensibles — prise d'un coefficient, finalisation, validation du
dernier item, calcul du classement, jokers — s'exécutent dans une transaction
avec `select_for_update()` sur la ligne `TierList` (et sur l'item lors d'un
joker). Deux requêtes simultanées sont donc sérialisées : la seconde observe
l'état déjà modifié et échoue proprement avec un message métier.

Deux tests couvrent explicitement ce point : création concurrente de la dernière
question coefficient 5, et double utilisation d'un même tour de joker.

---

## 9. Interaction du joker : sélection d'abord, glisser-déposer en complément

**Spec concernée :** §37, §45.3, §58.

Le glisser-déposer tactile via une librairie dédiée s'est révélé le maillon
fragile ; la spec autorise explicitement de lui préférer « sélection de l'item
puis choix du rang ».

**Décision :** la sélection est le mécanisme **principal** — universel, tactile
et accessible au clavier. Le glisser-déposer natif HTML5 vient en complément sur
les périphériques à pointeur. Les deux alimentent le même aperçu, et rien n'est
persisté avant « Valider mon joker ».

---

## 10. Une seule origine en production

**Spec concernée :** §6.2 (« politique SameSite cohérente avec l'architecture de
déploiement »), §64.

Le `Dockerfile` construit le frontend puis le fait servir par Django. API et SPA
partagent la même origine : les cookies `HttpOnly` + `SameSite=Lax` suffisent,
sans configuration CORS en production.

En développement, le serveur Vite proxifie `/api`, `/media` et `/admin` vers
Django, ce qui reproduit la même origine. La cible du proxy est `127.0.0.1` et
non `localhost` : ce dernier peut résoudre en IPv6 et atteindre un autre service
écoutant sur le même port.

---

## 11. « Non authentifié » est une réponse, pas une erreur

Côté frontend, `GET /api/auth/me` traduit un 401/403 en `null` plutôt qu'en
erreur. Sans cela, la requête restait en état d'erreur tout en conservant sa
dernière donnée connue, et l'interface continuait d'afficher l'utilisateur
précédent après une déconnexion.

De même, la déconnexion purge les données privées du cache **sans** vider la
requête d'authentification : la détruire détacherait son observateur, qui
continuerait d'exposer l'ancien utilisateur.

---

## 12. PostgreSQL partout, y compris pour les tests

**Spec concernée :** §3.4.

Aucun réglage ne bascule sur SQLite, pas même pour la suite de tests : les
contraintes d'unicité normalisée et les `CheckConstraint` doivent être vérifiées
sur le moteur réellement utilisé en production.

En local, `docker compose up -d postgres` expose PostgreSQL sur le port **5433**
pour ne pas entrer en conflit avec une instance déjà installée sur 5432.

## Service des images uploadées en production

`django.conf.urls.static.static()` ne renvoie aucune route dès que `DEBUG=False`.
Utilisé pour `MEDIA_URL`, il produit un bug qui n'apparaît qu'en production : les
requêtes `/media/...` ne sont plus routées, tombent dans le catch-all du SPA et
renvoient du HTML là où le navigateur attend une image.

Le routage des médias est donc déclaré explicitement, indépendamment de `DEBUG`,
via `django.views.static.serve`. Ce dernier s'appuie sur `safe_join`, ce qui
satisfait l'exigence de protection contre le path traversal (spec §51).

Les fichiers transitent par gunicorn plutôt que par un serveur dédié : sur
Railway il n'y a ni nginx ni CDN devant l'application, et le volume est monté
directement dans le conteneur. C'est un compromis assumé à l'échelle du produit ;
si le trafic média devenait significatif, la bonne évolution serait un stockage
objet (S3) plutôt qu'un réglage de serveur.
