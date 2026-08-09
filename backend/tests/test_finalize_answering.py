"""Finalisation, ordre aléatoire, questionnaire, autosave, verrouillage.

Spec §16, §17, §18, §20, §21, §22, §26.
"""

from __future__ import annotations

import pytest

from tests.helpers import answer_item, complete_questionnaire
from tierlists.constants import TierListStatus
from tierlists.models import Answer, ParticipantItemProgress, Question

pytestmark = pytest.mark.django_db


@pytest.fixture
def ready(make_tier_list, add_items, add_valid_questions, teo, laura, join):
    """Tier List prête à être finalisée : 2 participants, 4 items, 6 questions."""
    tier_list = make_tier_list(teo)
    join(tier_list, laura)
    items = add_items(tier_list, ["KFC", "Quick", "Burger King", "McDo"])
    questions = add_valid_questions(tier_list)
    return tier_list, items, questions


# ---------------------------------------------------------------------------
# Finalisation
# ---------------------------------------------------------------------------


def test_seul_le_createur_peut_finaliser(auth_client, laura, ready):
    tier_list, *_ = ready
    response = auth_client(laura).post(f"/api/tier-lists/{tier_list.pk}/finalize")
    assert response.status_code == 403
    assert response.data["code"] == "not_creator"


def test_finalisation_reussie(auth_client, teo, ready):
    tier_list, *_ = ready
    response = auth_client(teo).post(f"/api/tier-lists/{tier_list.pk}/finalize")
    assert response.status_code == 200
    tier_list.refresh_from_db()
    assert tier_list.status == TierListStatus.ANSWERING
    assert tier_list.finalized_at is not None


def test_finalisation_impossible_sans_item(auth_client, teo, make_tier_list, add_valid_questions):
    tier_list = make_tier_list(teo)
    add_valid_questions(tier_list)
    response = auth_client(teo).post(f"/api/tier-lists/{tier_list.pk}/finalize")
    assert response.status_code == 400
    assert "au moins un item" in response.data["detail"]


def test_finalisation_impossible_avec_cinq_questions(auth_client, teo, ready):
    tier_list, _items, questions = ready
    questions[0].delete()
    response = auth_client(teo).post(f"/api/tier-lists/{tier_list.pk}/finalize")
    assert response.status_code == 400
    assert response.data["code"] == "finalization_blocked"


def test_finalisation_impossible_avec_mauvaise_distribution(
    auth_client, teo, make_tier_list, add_items
):
    tier_list = make_tier_list(teo)
    add_items(tier_list, ["KFC"])
    # Six questions mais distribution 1,1,1,1,1,1 au lieu de 1,1,2,2,3,5.
    for index in range(6):
        Question.objects.create(
            tier_list=tier_list, text=f"Question numéro {index}.", coefficient=1, display_order=index
        )
    response = auth_client(teo).post(f"/api/tier-lists/{tier_list.pk}/finalize")
    assert response.status_code == 400
    assert "1, 1, 2, 2, 3 et 5" in response.data["detail"]


def test_double_finalisation_refusee(auth_client, teo, ready):
    tier_list, *_ = ready
    client = auth_client(teo)
    client.post(f"/api/tier-lists/{tier_list.pk}/finalize")
    response = client.post(f"/api/tier-lists/{tier_list.pk}/finalize")
    assert response.status_code == 409


def test_plus_personne_ne_peut_rejoindre_apres_finalisation(auth_client, teo, paul, ready):
    tier_list, *_ = ready
    auth_client(teo).post(f"/api/tier-lists/{tier_list.pk}/finalize")
    response = auth_client(paul).post(
        "/api/tier-lists/join", {"code": tier_list.invite_code}, format="json"
    )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Ordre des items (spec §17)
# ---------------------------------------------------------------------------


def test_chaque_participant_recoit_son_propre_ordre(auth_client, teo, laura, ready, add_items):
    tier_list, *_ = ready
    add_items(tier_list, [f"Item {i}" for i in range(20)])
    auth_client(teo).post(f"/api/tier-lists/{tier_list.pk}/finalize")

    orders = {}
    for user in (teo, laura):
        response = auth_client(user).get(f"/api/tier-lists/{tier_list.pk}/answering")
        orders[user.username] = [item["id"] for item in response.data["items"]]

    assert sorted(orders["teo"]) == sorted(orders["laura"])
    # Sur 24 items, deux ordres aléatoires identiques sont improbables.
    assert orders["teo"] != orders["laura"]


def test_l_ordre_reste_stable_entre_deux_rafraichissements(auth_client, teo, ready):
    tier_list, *_ = ready
    client = auth_client(teo)
    client.post(f"/api/tier-lists/{tier_list.pk}/finalize")

    first = [i["id"] for i in client.get(f"/api/tier-lists/{tier_list.pk}/answering").data["items"]]
    second = [i["id"] for i in client.get(f"/api/tier-lists/{tier_list.pk}/answering").data["items"]]
    assert first == second


def test_les_questions_gardent_le_meme_ordre_pour_tous(auth_client, teo, laura, ready):
    tier_list, *_ = ready
    auth_client(teo).post(f"/api/tier-lists/{tier_list.pk}/finalize")
    orders = [
        [q["id"] for q in auth_client(u).get(f"/api/tier-lists/{tier_list.pk}/answering").data["questions"]]
        for u in (teo, laura)
    ]
    assert orders[0] == orders[1]


# ---------------------------------------------------------------------------
# Réponses (spec §19, §20)
# ---------------------------------------------------------------------------


@pytest.fixture
def answering(auth_client, teo, ready):
    tier_list, items, questions = ready
    auth_client(teo).post(f"/api/tier-lists/{tier_list.pk}/finalize")
    return tier_list, items, questions


@pytest.mark.parametrize("value", [0, 10, -1, 12])
def test_valeur_hors_echelle_refusee(auth_client, teo, answering, value):
    tier_list, items, questions = answering
    response = auth_client(teo).put(
        f"/api/tier-lists/{tier_list.pk}/items/{items[0].pk}/answers/{questions[0].pk}",
        {"value": value},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.parametrize("value", [1, 5, 9])
def test_valeurs_valides_acceptees(auth_client, teo, answering, value):
    tier_list, items, questions = answering
    response = auth_client(teo).put(
        f"/api/tier-lists/{tier_list.pk}/items/{items[0].pk}/answers/{questions[0].pk}",
        {"value": value},
        format="json",
    )
    assert response.status_code == 200


def test_autosave_ecrase_la_valeur_precedente(auth_client, teo, answering):
    tier_list, items, questions = answering
    client = auth_client(teo)
    url = f"/api/tier-lists/{tier_list.pk}/items/{items[0].pk}/answers/{questions[0].pk}"
    client.put(url, {"value": 3}, format="json")
    client.put(url, {"value": 8}, format="json")
    assert Answer.objects.filter(item=items[0], question=questions[0]).count() == 1
    assert Answer.objects.get(item=items[0], question=questions[0]).value == 8


def test_validation_impossible_avec_une_reponse_manquante(auth_client, teo, answering):
    tier_list, items, questions = answering
    client = auth_client(teo)
    for question in questions[:5]:
        client.put(
            f"/api/tier-lists/{tier_list.pk}/items/{items[0].pk}/answers/{question.pk}",
            {"value": 5},
            format="json",
        )
    response = client.post(f"/api/tier-lists/{tier_list.pk}/items/{items[0].pk}/validate")
    assert response.status_code == 400
    assert response.data["code"] == "missing_answers"


def test_apres_validation_les_reponses_sont_verrouillees(auth_client, teo, answering):
    """Le backend impose la règle, pas seulement le frontend (spec §20)."""
    tier_list, items, questions = answering
    client = auth_client(teo)
    answer_item(client, tier_list, items[0].pk, {q.pk: 6 for q in questions})

    response = client.put(
        f"/api/tier-lists/{tier_list.pk}/items/{items[0].pk}/answers/{questions[0].pk}",
        {"value": 9},
        format="json",
    )
    assert response.status_code == 409
    assert response.data["code"] == "item_already_validated"
    assert Answer.objects.get(item=items[0], question=questions[0]).value == 6


def test_double_validation_refusee(auth_client, teo, answering):
    tier_list, items, questions = answering
    client = auth_client(teo)
    answer_item(client, tier_list, items[0].pk, {q.pk: 6 for q in questions})
    response = client.post(f"/api/tier-lists/{tier_list.pk}/items/{items[0].pk}/validate")
    assert response.status_code == 409


def test_on_ne_peut_pas_repondre_pour_un_autre(auth_client, teo, laura, answering):
    """Chaque participant n'écrit que ses propres réponses (spec §50)."""
    tier_list, items, questions = answering
    auth_client(laura).put(
        f"/api/tier-lists/{tier_list.pk}/items/{items[0].pk}/answers/{questions[0].pk}",
        {"value": 9},
        format="json",
    )
    laura_participant = tier_list.participants.get(user=laura)
    teo_participant = tier_list.participants.get(user=teo)
    assert Answer.objects.filter(participant=laura_participant).count() == 1
    assert Answer.objects.filter(participant=teo_participant).count() == 0


# ---------------------------------------------------------------------------
# Progression (spec §21, §22)
# ---------------------------------------------------------------------------


def test_progression_du_participant(auth_client, teo, answering):
    tier_list, items, questions = answering
    client = auth_client(teo)
    answer_item(client, tier_list, items[0].pk, {q.pk: 5 for q in questions})

    response = client.get(f"/api/tier-lists/{tier_list.pk}/answering")
    assert response.data["progress"] == {
        "validated_items": 1,
        "total_items": 4,
        "progress_percent": 25,
        "has_finished": False,
    }


def test_on_voit_la_progression_des_autres_pas_leurs_reponses(auth_client, teo, laura, answering):
    tier_list, items, questions = answering
    answer_item(auth_client(laura), tier_list, items[0].pk, {q.pk: 9 for q in questions})

    response = auth_client(teo).get(f"/api/tier-lists/{tier_list.pk}/answering")
    laura_row = next(p for p in response.data["participants"] if p["user"]["username"] == "laura")
    assert laura_row["progress_percent"] == 25
    assert laura_row["has_finished"] is False
    # Aucune valeur de réponse ne transite.
    assert "answers" not in laura_row
    assert "9" not in str(laura_row)


def test_le_classement_n_est_pas_expose_avant_la_fin(auth_client, teo, laura, answering):
    tier_list, *_ = answering
    complete_questionnaire(auth_client(teo), tier_list, value=8)

    response = auth_client(teo).get(f"/api/tier-lists/{tier_list.pk}/ranking")
    assert response.status_code == 409
    assert response.data["code"] == "ranking_not_ready"


def test_participant_marque_termine_quand_tout_est_valide(auth_client, teo, answering):
    tier_list, *_ = answering
    complete_questionnaire(auth_client(teo), tier_list, value=7)

    participant = tier_list.participants.get(user=teo)
    assert participant.answering_completed_at is not None
    assert not ParticipantItemProgress.objects.filter(
        participant=participant, is_validated=False
    ).exists()


def test_bascule_en_joker_quand_tout_le_monde_a_termine(auth_client, teo, laura, answering):
    tier_list, *_ = answering
    complete_questionnaire(auth_client(teo), tier_list, value=7)
    tier_list.refresh_from_db()
    assert tier_list.status == TierListStatus.ANSWERING

    complete_questionnaire(auth_client(laura), tier_list, value=4)
    tier_list.refresh_from_db()
    assert tier_list.status == TierListStatus.JOKER
    assert tier_list.scores.count() == 4
