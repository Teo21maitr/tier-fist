"""Items : unicité normalisée, images, collaboration (spec §14, §12, §60)."""

from __future__ import annotations

import pytest

from tierlists.constants import TierListStatus
from tierlists.models import Item

pytestmark = pytest.mark.django_db


def test_creation_d_un_item_sans_image(auth_client, teo, make_tier_list):
    tier_list = make_tier_list(teo)
    response = auth_client(teo).post(
        f"/api/tier-lists/{tier_list.pk}/items", {"name": "KFC"}, format="json"
    )
    assert response.status_code == 201
    assert response.data["name"] == "KFC"
    # Sans image, le frontend affiche le placeholder Laurent Baffist.
    assert response.data["has_image"] is False
    assert response.data["image_url"] is None


def test_item_avec_url_distante(auth_client, teo, make_tier_list):
    tier_list = make_tier_list(teo)
    response = auth_client(teo).post(
        f"/api/tier-lists/{tier_list.pk}/items",
        {"name": "Burger King", "external_image_url": "https://example.com/bk.png"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["image_url"] == "https://example.com/bk.png"


def test_url_invalide_refusee(auth_client, teo, make_tier_list):
    tier_list = make_tier_list(teo)
    response = auth_client(teo).post(
        f"/api/tier-lists/{tier_list.pk}/items",
        {"name": "X", "external_image_url": "javascript:alert(1)"},
        format="json",
    )
    assert response.status_code == 400


def test_item_avec_upload(auth_client, teo, make_tier_list, png_upload):
    tier_list = make_tier_list(teo)
    response = auth_client(teo).post(
        f"/api/tier-lists/{tier_list.pk}/items",
        {"name": "Quick", "uploaded_image": png_upload()},
        format="multipart",
    )
    assert response.status_code == 201
    item = Item.objects.get(pk=response.data["id"])
    # Nom de fichier généré côté serveur, pas celui du client (spec §51).
    assert "photo" not in item.uploaded_image.name
    assert item.uploaded_image.name.startswith("items/")
    item.uploaded_image.delete(save=True)


def test_upload_non_image_refuse(auth_client, teo, make_tier_list):
    from django.core.files.uploadedfile import SimpleUploadedFile

    tier_list = make_tier_list(teo)
    fake = SimpleUploadedFile("evil.png", b"<?php echo 1; ?>", content_type="image/png")
    response = auth_client(teo).post(
        f"/api/tier-lists/{tier_list.pk}/items",
        {"name": "X", "uploaded_image": fake},
        format="multipart",
    )
    assert response.status_code == 400


def test_upload_trop_lourd_refuse(auth_client, teo, make_tier_list, settings):
    from django.core.files.uploadedfile import SimpleUploadedFile

    settings.MAX_UPLOAD_IMAGE_SIZE = 10
    tier_list = make_tier_list(teo)
    heavy = SimpleUploadedFile("big.png", b"x" * 500, content_type="image/png")
    response = auth_client(teo).post(
        f"/api/tier-lists/{tier_list.pk}/items",
        {"name": "X", "uploaded_image": heavy},
        format="multipart",
    )
    assert response.status_code == 400


def test_l_upload_prime_sur_l_url(auth_client, teo, make_tier_list, png_upload):
    """Règle de priorité explicite (spec §48.4)."""
    tier_list = make_tier_list(teo)
    response = auth_client(teo).post(
        f"/api/tier-lists/{tier_list.pk}/items",
        {
            "name": "Quick",
            "uploaded_image": png_upload(),
            "external_image_url": "https://example.com/x.png",
        },
        format="multipart",
    )
    item = Item.objects.get(pk=response.data["id"])
    assert item.uploaded_image
    assert item.external_image_url == ""
    item.uploaded_image.delete(save=True)


# --- Unicité ----------------------------------------------------------------


@pytest.mark.parametrize("duplicate", ["kfc", " KFC ", "KfC", "KFC  "])
def test_nom_duplique_refuse_quelle_que_soit_la_casse(
    auth_client, teo, make_tier_list, duplicate
):
    tier_list = make_tier_list(teo)
    client = auth_client(teo)
    client.post(f"/api/tier-lists/{tier_list.pk}/items", {"name": "KFC"}, format="json")
    response = client.post(
        f"/api/tier-lists/{tier_list.pk}/items", {"name": duplicate}, format="json"
    )
    assert response.status_code == 400
    assert "existe déjà" in response.data["detail"]


def test_le_meme_nom_est_permis_dans_deux_tier_lists(auth_client, teo, make_tier_list):
    first = make_tier_list(teo, name="A")
    second = make_tier_list(teo, name="B")
    client = auth_client(teo)
    assert client.post(f"/api/tier-lists/{first.pk}/items", {"name": "KFC"}, format="json").status_code == 201
    assert client.post(f"/api/tier-lists/{second.pk}/items", {"name": "KFC"}, format="json").status_code == 201


def test_renommer_un_item_vers_un_nom_existant_est_refuse(auth_client, teo, make_tier_list, add_items):
    tier_list = make_tier_list(teo)
    kfc, quick = add_items(tier_list, ["KFC", "Quick"])
    response = auth_client(teo).patch(
        f"/api/tier-lists/{tier_list.pk}/items/{quick.pk}", {"name": "kfc"}, format="json"
    )
    assert response.status_code == 400


def test_renommer_un_item_avec_son_propre_nom_reste_possible(auth_client, teo, make_tier_list, add_items):
    tier_list = make_tier_list(teo)
    (kfc,) = add_items(tier_list, ["KFC"])
    response = auth_client(teo).patch(
        f"/api/tier-lists/{tier_list.pk}/items/{kfc.pk}", {"name": "KFC "}, format="json"
    )
    assert response.status_code == 200


# --- Collaboration ----------------------------------------------------------


def test_tout_participant_peut_creer_modifier_supprimer(
    auth_client, teo, laura, make_tier_list, join, add_items
):
    """Pendant DRAFT, tous les participants ont les mêmes droits (spec §12)."""
    tier_list = make_tier_list(teo)
    join(tier_list, laura)
    (kfc,) = add_items(tier_list, ["KFC"])
    client = auth_client(laura)

    assert client.post(f"/api/tier-lists/{tier_list.pk}/items", {"name": "Quick"}, format="json").status_code == 201
    assert client.patch(
        f"/api/tier-lists/{tier_list.pk}/items/{kfc.pk}", {"name": "KFC Wings"}, format="json"
    ).status_code == 200
    assert client.delete(f"/api/tier-lists/{tier_list.pk}/items/{kfc.pk}").status_code == 204


def test_un_non_participant_ne_peut_rien_faire(auth_client, teo, laura, make_tier_list):
    tier_list = make_tier_list(teo)
    response = auth_client(laura).post(
        f"/api/tier-lists/{tier_list.pk}/items", {"name": "KFC"}, format="json"
    )
    assert response.status_code == 404


def test_items_figes_apres_finalisation(auth_client, teo, make_tier_list, add_items):
    tier_list = make_tier_list(teo)
    (kfc,) = add_items(tier_list, ["KFC"])
    tier_list.status = TierListStatus.ANSWERING
    tier_list.save()
    client = auth_client(teo)

    assert client.post(f"/api/tier-lists/{tier_list.pk}/items", {"name": "Quick"}, format="json").status_code == 409
    assert client.patch(
        f"/api/tier-lists/{tier_list.pk}/items/{kfc.pk}", {"name": "Autre"}, format="json"
    ).status_code == 409
    assert client.delete(f"/api/tier-lists/{tier_list.pk}/items/{kfc.pk}").status_code == 409


def test_un_seul_item_suffit(auth_client, teo, make_tier_list, add_items, add_valid_questions):
    """Il n'existe pas de nombre minimum supérieur à 1 (spec §16)."""
    tier_list = make_tier_list(teo)
    add_items(tier_list, ["KFC"])
    add_valid_questions(tier_list)
    response = auth_client(teo).post(f"/api/tier-lists/{tier_list.pk}/finalize")
    assert response.status_code == 200
