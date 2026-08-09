import re

from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as serve_media

from config.views import healthz, spa_index

urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("tierlists.urls")),
]

# Les images uploadées vivent sur le volume Railway et doivent être servies en
# production comme en développement.
#
# On n'utilise volontairement pas `django.conf.urls.static.static()` : ce helper
# ne renvoie *aucune* route dès que DEBUG=False. Les requêtes /media/... seraient
# alors capturées par le catch-all du SPA, qui répondrait du HTML là où le
# navigateur attend une image — les images fonctionneraient en local et
# casseraient silencieusement en production.
#
# `django.views.static.serve` s'appuie sur `safe_join` : une requête du type
# /media/../../etc/passwd est rejetée (spec §51, protection path traversal).
#
# Ce service passe par gunicorn, ce qui est acceptable à l'échelle du produit :
# il n'y a ni nginx ni CDN devant l'application sur Railway. Voir docs/DECISIONS.md.
_media_prefix = re.escape(settings.MEDIA_URL.lstrip("/"))
urlpatterns += [
    re_path(
        rf"^{_media_prefix}(?P<path>.*)$",
        serve_media,
        {"document_root": settings.MEDIA_ROOT},
        name="media",
    )
]

# Catch-all : toutes les autres routes servent le SPA React (React Router gère
# ensuite la navigation côté client). Les préfixes api/admin/media/static sont
# déjà consommés ci-dessus.
urlpatterns += [path("", spa_index), path("<path:resource>", spa_index)]

admin.site.site_header = "Tier Fist — administration"
admin.site.site_title = "Tier Fist"
admin.site.index_title = "Gestion des comptes et des Tier Lists"
