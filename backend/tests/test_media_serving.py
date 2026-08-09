"""Service des images uploadées (spec §14.3, §51).

Ces tests couvrent une régression réelle : avec
``django.conf.urls.static.static()``, les médias n'étaient routés que si
``DEBUG=True``. En production, /media/... tombait dans le catch-all du SPA et
renvoyait du HTML au lieu de l'image — cassure invisible en développement.
"""

from __future__ import annotations

import pytest
from django.urls import resolve

from config.views import spa_index

pytestmark = pytest.mark.django_db


def test_les_medias_ne_sont_pas_captures_par_le_spa():
    """Le routage des médias ne doit dépendre d'aucun réglage DEBUG."""
    match = resolve("/media/items/exemple.png")
    assert match.func is not spa_index
    assert match.func.__module__ == "django.views.static"


def test_une_image_uploadee_est_telechargeable(auth_client, teo, make_tier_list, png_upload):
    tier_list = make_tier_list(teo)
    client = auth_client(teo)
    created = client.post(
        f"/api/tier-lists/{tier_list.pk}/items",
        {"name": "Quick", "uploaded_image": png_upload()},
        format="multipart",
    )
    assert created.status_code == 201

    from tierlists.models import Item

    item = Item.objects.get(pk=created.data["id"])
    try:
        response = client.get(item.uploaded_image.url)
        assert response.status_code == 200
        # Une image, surtout pas la page HTML du SPA.
        assert response["Content-Type"] == "image/png"
        body = b"".join(response.streaming_content)
        assert body.startswith(b"\x89PNG")
    finally:
        item.uploaded_image.delete(save=True)


def test_le_path_traversal_est_refuse(auth_client, teo):
    """safe_join doit rejeter une tentative de sortie de MEDIA_ROOT."""
    response = auth_client(teo).get("/media/../../etc/passwd")
    assert response.status_code in (400, 404)


def test_un_media_inexistant_renvoie_404(auth_client, teo):
    """Et surtout pas la page du SPA en 200."""
    response = auth_client(teo).get("/media/items/inexistant.png")
    assert response.status_code == 404
