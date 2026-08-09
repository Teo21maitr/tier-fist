from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render


def spa_index(request, resource: str = ""):
    """Sert l'application React construite par Vite.

    En développement, le frontend tourne sur le serveur Vite : ce fallback n'est
    donc utilisé que si l'on ouvre directement le backend.
    """
    index_file = settings.FRONTEND_DIST_DIR / "index.html"
    if not index_file.exists():
        return HttpResponse(
            "<h1>Tier Fist</h1>"
            "<p>Le frontend n'est pas construit. En développement, lance "
            "<code>npm run dev</code> dans <code>frontend/</code>.</p>",
            status=200,
            content_type="text/html; charset=utf-8",
        )
    return render(request, "index.html")
