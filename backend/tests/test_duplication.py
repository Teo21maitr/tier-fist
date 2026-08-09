"""Duplication d'une Tier List (spec §42)."""

from __future__ import annotations

import pytest

from tests.helpers import complete_questionnaire
from tierlists.constants import TierListStatus
from tierlists.models import Item, TierList

pytestmark = pytest.mark.django_db


@pytest.fixture
def source(auth_client, teo, laura, join, make_tier_list, add_items, add_valid_questions):
    tier_list = make_tier_list(teo, name="Fast-food", theme="Restauration rapide")
    join(tier_list, laura)
    tier_list.rank_1_name = "Légendaire"
    tier_list.save()
    add_items(tier_list, ["KFC", "Quick", "McDo"])
    add_valid_questions(tier_list)
    return tier_list


def test_la_copie_reprend_la_structure(auth_client, teo, source):
    response = auth_client(teo).post(f"/api/tier-lists/{source.pk}/duplicate")
    assert response.status_code == 201

    copy = TierList.objects.get(pk=response.data["id"])
    assert copy.name == "Copie de Fast-food"
    assert copy.theme == "Restauration rapide"
    assert copy.rank_1_name == "Légendaire"
    assert copy.status == TierListStatus.DRAFT
    assert sorted(copy.items.values_list("name", flat=True)) == ["KFC", "McDo", "Quick"]
    assert sorted(copy.questions.values_list("coefficient", flat=True)) == [1, 1, 2, 2, 3, 5]


def test_la_copie_recoit_un_nouveau_code(auth_client, teo, source):
    response = auth_client(teo).post(f"/api/tier-lists/{source.pk}/duplicate")
    assert response.data["invite_code"] != source.invite_code


def test_le_duplicateur_devient_createur_et_seul_participant(auth_client, laura, source):
    """Même un participant non créateur peut dupliquer : il devient créateur de la copie."""
    response = auth_client(laura).post(f"/api/tier-lists/{source.pk}/duplicate")
    copy = TierList.objects.get(pk=response.data["id"])
    assert copy.creator == laura
    assert list(copy.participants.values_list("user__username", flat=True)) == ["laura"]


def test_la_copie_ne_reprend_ni_reponses_ni_jokers(auth_client, teo, laura, source):
    from tierlists.models import Answer, JokerAction, ParticipantItemProgress

    auth_client(teo).post(f"/api/tier-lists/{source.pk}/finalize")
    complete_questionnaire(auth_client(teo), source, value=8)
    complete_questionnaire(auth_client(laura), source, value=4)
    source.refresh_from_db()
    assert source.status == TierListStatus.JOKER

    response = auth_client(teo).post(f"/api/tier-lists/{source.pk}/duplicate")
    copy = TierList.objects.get(pk=response.data["id"])

    assert not Answer.objects.filter(participant__tier_list=copy).exists()
    assert not ParticipantItemProgress.objects.filter(participant__tier_list=copy).exists()
    assert not JokerAction.objects.filter(tier_list=copy).exists()
    assert not copy.scores.exists()
    assert copy.completed_at is None and copy.finalized_at is None
    # Les items de la copie ne sont pas verrouillés par un joker.
    assert not copy.items.filter(joker_locked=True).exists()


def test_nom_personnalise(auth_client, teo, source):
    response = auth_client(teo).post(
        f"/api/tier-lists/{source.pk}/duplicate", {"name": "Saison 2"}, format="json"
    )
    assert response.data["name"] == "Saison 2"


def test_les_images_uploadees_sont_copiees(auth_client, teo, source, png_upload):
    item = source.items.first()
    item.uploaded_image.save("original.png", png_upload(), save=True)

    response = auth_client(teo).post(f"/api/tier-lists/{source.pk}/duplicate")
    copy = TierList.objects.get(pk=response.data["id"])
    clone = copy.items.get(name=item.name)

    assert clone.uploaded_image
    # Fichier distinct : supprimer une Tier List n'ampute pas l'autre.
    assert clone.uploaded_image.name != item.uploaded_image.name
    assert clone.uploaded_image.read() == item.uploaded_image.read()

    item.uploaded_image.delete(save=True)
    clone.uploaded_image.delete(save=True)


def test_les_urls_distantes_sont_copiees(auth_client, teo, source):
    item = source.items.first()
    item.external_image_url = "https://example.com/kfc.png"
    item.save()

    response = auth_client(teo).post(f"/api/tier-lists/{source.pk}/duplicate")
    copy = TierList.objects.get(pk=response.data["id"])
    assert copy.items.get(name=item.name).external_image_url == "https://example.com/kfc.png"


def test_un_non_participant_ne_peut_pas_dupliquer(auth_client, make_user, source):
    intrus = make_user("intrus")
    assert auth_client(intrus).post(f"/api/tier-lists/{source.pk}/duplicate").status_code == 404


def test_la_source_n_est_pas_modifiee(auth_client, teo, source):
    auth_client(teo).post(f"/api/tier-lists/{source.pk}/duplicate")
    source.refresh_from_db()
    assert source.items.count() == 3
    assert source.participants.count() == 2
    assert Item.objects.filter(tier_list=source).count() == 3
