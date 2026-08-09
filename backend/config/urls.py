from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from config.views import healthz, spa_index

urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("tierlists.urls")),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Catch-all : toutes les autres routes servent le SPA React (React Router gère
# ensuite la navigation côté client). Les préfixes api/admin/media/static sont
# déjà consommés ci-dessus.
urlpatterns += [path("", spa_index), path("<path:resource>", spa_index)]

admin.site.site_header = "Tier Fist — administration"
admin.site.site_title = "Tier Fist"
admin.site.index_title = "Gestion des comptes et des Tier Lists"
