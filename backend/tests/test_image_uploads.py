"""Formats d'image acceptés à l'upload (spec §14.2, §51).

Le contenu réel fait foi : ni l'extension ni le Content-Type annoncé ne sont
crus sur parole. Les photos HEIC des iPhone sont converties en JPEG, faute de
quoi Chrome et Firefox afficheraient une image cassée.
"""

from __future__ import annotations

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from common.uploads import ALLOWED_IMAGE_FORMATS
from tierlists.models import Item

pytestmark = pytest.mark.django_db


def build_image(image_format: str, name: str, content_type: str = "image/png"):
    """Fabrique un fichier réellement encodé dans le format demandé."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), (10, 120, 200)).save(buffer, format=image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


def upload_item(client, tier_list, uploaded, name="Item"):
    return client.post(
        f"/api/tier-lists/{tier_list.pk}/items",
        {"name": name, "uploaded_image": uploaded},
        format="multipart",
    )


@pytest.mark.parametrize(
    "image_format,expected_extension",
    [("JPEG", ".jpg"), ("PNG", ".png"), ("GIF", ".gif"), ("WEBP", ".webp")],
)
def test_formats_acceptes_et_stockes_tels_quels(
    auth_client, teo, make_tier_list, image_format, expected_extension
):
    tier_list = make_tier_list(teo)
    uploaded = build_image(image_format, f"photo.{image_format.lower()}")
    response = upload_item(auth_client(teo), tier_list, uploaded)

    assert response.status_code == 201, response.data
    item = Item.objects.get(pk=response.data["id"])
    try:
        assert item.uploaded_image.name.endswith(expected_extension)
    finally:
        item.uploaded_image.delete(save=True)


def test_une_photo_heic_est_convertie_en_jpeg(auth_client, teo, make_tier_list):
    """Chrome et Firefox n'affichent pas le HEIC : on stocke du JPEG."""
    from PIL import Image

    tier_list = make_tier_list(teo)
    uploaded = build_image("HEIF", "IMG_4821.HEIC", content_type="image/heic")
    response = upload_item(auth_client(teo), tier_list, uploaded)

    assert response.status_code == 201, response.data
    item = Item.objects.get(pk=response.data["id"])
    try:
        assert item.uploaded_image.name.endswith(".jpg")
        item.uploaded_image.open("rb")
        assert Image.open(item.uploaded_image).format == "JPEG"
    finally:
        item.uploaded_image.close()
        item.uploaded_image.delete(save=True)


def test_un_avatar_heic_est_aussi_converti(auth_client, teo):
    from PIL import Image

    uploaded = build_image("HEIF", "selfie.heic", content_type="image/heic")
    response = auth_client(teo).patch("/api/auth/me", {"avatar": uploaded}, format="multipart")

    assert response.status_code == 200, response.data
    teo.refresh_from_db()
    try:
        assert teo.avatar.name.endswith(".jpg")
        teo.avatar.open("rb")
        assert Image.open(teo.avatar).format == "JPEG"
    finally:
        teo.avatar.close()
        teo.avatar.delete(save=True)


def test_un_format_non_supporte_est_refuse(auth_client, teo, make_tier_list):
    """Un BMP est une vraie image, mais ne fait pas partie des formats retenus."""
    tier_list = make_tier_list(teo)
    uploaded = build_image("BMP", "image.bmp", content_type="image/bmp")
    response = upload_item(auth_client(teo), tier_list, uploaded)

    assert response.status_code == 400
    assert "Format d'image non supporté" in response.data["detail"]


def test_l_extension_ne_suffit_pas_a_tromper_la_validation(auth_client, teo, make_tier_list):
    """Un script renommé en .png reste refusé : c'est le contenu qui décide."""
    tier_list = make_tier_list(teo)
    piege = SimpleUploadedFile(
        "photo.png", b"<?php system($_GET['c']); ?>", content_type="image/png"
    )
    response = upload_item(auth_client(teo), tier_list, piege)

    assert response.status_code == 400
    # Le refus peut venir d'ImageField (message Django) ou de notre validateur :
    # dans les deux cas l'utilisateur lit un message clair en français.
    assert "image valide" in response.data["detail"]


def test_le_nom_de_fichier_est_toujours_regenere(auth_client, teo, make_tier_list):
    """Aucune confiance dans le nom fourni par le client (spec §51)."""
    tier_list = make_tier_list(teo)
    uploaded = build_image("PNG", "../../etc/passwd.png")
    response = upload_item(auth_client(teo), tier_list, uploaded)

    assert response.status_code == 201
    item = Item.objects.get(pk=response.data["id"])
    try:
        assert ".." not in item.uploaded_image.name
        assert "passwd" not in item.uploaded_image.name
        assert item.uploaded_image.name.startswith("items/")
    finally:
        item.uploaded_image.delete(save=True)


def test_le_decodeur_heif_est_branche_au_demarrage():
    """Sinon ImageField de Django refuserait le HEIC avant notre conversion."""
    from PIL import Image

    assert "HEIF" in Image.OPEN


def test_les_formats_stockes_restent_affichables_par_un_navigateur():
    """Garde-fou : n'ajouter aux formats stockés que ce qui s'affiche partout."""
    assert set(ALLOWED_IMAGE_FORMATS) == {"JPEG", "PNG", "GIF", "WEBP"}
