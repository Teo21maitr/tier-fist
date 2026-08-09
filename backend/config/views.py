from django.conf import settings
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render


def healthz(request):
    """Sonde de santé utilisée par Railway pendant le déploiement.

    Vérifie que l'application répond *et* que la base est joignable : un
    ``DATABASE_URL`` mal configuré doit faire échouer le déploiement plutôt que
    de mettre en ligne une version cassée.

    Cette route est exemptée de la redirection HTTPS (voir ``SECURE_REDIRECT_EXEMPT``) :
    la sonde interroge le conteneur en HTTP, sans passer par le proxy TLS.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"status": "error", "database": "unreachable"}, status=503)
    return JsonResponse({"status": "ok"})


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
