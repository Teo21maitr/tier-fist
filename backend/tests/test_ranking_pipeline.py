"""Calcul des scores en base et restitution des résultats (spec §24, §25, §32, §61)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.helpers import complete_questionnaire
from tierlists.constants import TierListStatus
from tierlists.models import Answer
from tierlists.services.ranking import global_score_decimal

pytestmark = pytest.mark.django_db


@pytest.fixture
def played(auth_client, teo, laura, join, make_tier_list, add_items, add_valid_questions):
    """Partie à 2 joueurs et 3 items, finalisée et prête à recevoir des réponses."""
    tier_list = make_tier_list(teo)
    join(tier_list, laura)
    items = add_items(tier_list, ["KFC", "Quick", "McDo"])
    questions = add_valid_questions(tier_list)
    auth_client(teo).post(f"/api/tier-lists/{tier_list.pk}/finalize")
    return tier_list, items, questions


def test_exemple_complet_de_score_spec_61(auth_client, teo, laura, played):
    """Teo 106/14, Laura 114/14, score collectif 220/28 ≈ 7.857."""
    tier_list, items, questions = played
    kfc = items[0]

    # coefficients dans l'ordre : 1, 1, 2, 2, 3, 5
    teo_values = [7, 8, 6, 9, 7, 8]  # 7+8+12+18+21+40 = 106
    laura_values = [9, 9, 8, 8, 8, 8]  # 9+9+16+16+24+40 = 114

    for user, values in ((teo, teo_values), (laura, laura_values)):
        client = auth_client(user)
        for question, value in zip(questions, values, strict=False):
            client.put(
                f"/api/tier-lists/{tier_list.pk}/items/{kfc.pk}/answers/{question.pk}",
                {"value": value},
                format="json",
            )
        client.post(f"/api/tier-lists/{tier_list.pk}/items/{kfc.pk}/validate")

    # On termine le reste pour déclencher le calcul.
    complete_questionnaire(auth_client(teo), tier_list, value=1)
    complete_questionnaire(auth_client(laura), tier_list, value=1)

    tier_list.refresh_from_db()
    assert tier_list.status == TierListStatus.JOKER

    # 220 / 28 = 7.857142857..., conservé à 10 décimales.
    score = tier_list.scores.get(item=kfc)
    assert score.global_score == Decimal("7.8571428571")

    detail = auth_client(teo).get(
        f"/api/tier-lists/{tier_list.pk}/items/{kfc.pk}/result-detail"
    )
    assert detail.data["global_score"] == "7.86"
    scores_individuels = sorted(row["score"] for row in detail.data["participants"])
    assert scores_individuels == ["7.57", "8.14"]


def test_formule_du_score_collectif():
    """Spec §25 : tous les joueurs ont le même poids."""
    # 2 participants, somme pondérée totale = 220 -> 220 / (14 × 2) = 7.857142857...
    assert global_score_decimal(220, 2) == Decimal("7.8571428571")
    # Un score reste borné entre 1 et 9.
    assert global_score_decimal(14 * 3, 3) == Decimal("1")
    assert global_score_decimal(14 * 9 * 3, 3) == Decimal("9")


def test_le_classement_utilise_les_scores_collectifs(auth_client, teo, laura, played):
    tier_list, items, _questions = played
    kfc, quick, mcdo = items

    # KFC noté 9 par les deux, Quick 5, McDo 1.
    per_item = {kfc.pk: 9, quick.pk: 5, mcdo.pk: 1}
    complete_questionnaire(auth_client(teo), tier_list, per_item=per_item)
    complete_questionnaire(auth_client(laura), tier_list, per_item=per_item)

    response = auth_client(teo).get(f"/api/tier-lists/{tier_list.pk}/ranking")
    assert response.status_code == 200
    ranks = {rank["number"]: [item["name"] for item in rank["items"]] for rank in response.data["ranks"]}
    assert ranks[1] == ["KFC"]
    assert ranks[2] == ["Quick"]
    assert ranks[3] == ["McDo"]
    assert ranks[4] == []
    assert ranks[5] == []
    assert response.data["is_final"] is False


def test_moyenne_par_question(auth_client, teo, laura, played):
    tier_list, items, questions = played
    kfc = items[0]

    for user, value in ((teo, 8), (laura, 6)):
        client = auth_client(user)
        for question in questions:
            client.put(
                f"/api/tier-lists/{tier_list.pk}/items/{kfc.pk}/answers/{question.pk}",
                {"value": value},
                format="json",
            )
        client.post(f"/api/tier-lists/{tier_list.pk}/items/{kfc.pk}/validate")
    complete_questionnaire(auth_client(teo), tier_list, value=5)
    complete_questionnaire(auth_client(laura), tier_list, value=5)

    detail = auth_client(teo).get(
        f"/api/tier-lists/{tier_list.pk}/items/{kfc.pk}/result-detail"
    ).data
    assert all(row["average"] == "7.00" for row in detail["questions"])
    # Après la phase de réponses, les réponses individuelles deviennent consultables.
    assert len(detail["participants"]) == 2
    assert all(row["answers"] for row in detail["participants"])


def test_le_detail_est_inaccessible_avant_la_fin(auth_client, teo, played):
    tier_list, items, _ = played
    response = auth_client(teo).get(
        f"/api/tier-lists/{tier_list.pk}/items/{items[0].pk}/result-detail"
    )
    assert response.status_code == 409


def test_les_coefficients_redeviennent_visibles_apres_le_classement(
    auth_client, teo, laura, played
):
    tier_list, *_ = played
    complete_questionnaire(auth_client(teo), tier_list, value=5)
    complete_questionnaire(auth_client(laura), tier_list, value=5)
    response = auth_client(teo).get(f"/api/tier-lists/{tier_list.pk}/questions")
    assert "coefficient" in response.data[0]


def test_le_classement_n_est_calcule_qu_une_fois(auth_client, teo, laura, played):
    tier_list, *_ = played
    complete_questionnaire(auth_client(teo), tier_list, value=5)
    complete_questionnaire(auth_client(laura), tier_list, value=5)

    tier_list.refresh_from_db()
    algorithm_ranks = {s.item_id: s.algorithm_rank for s in tier_list.scores.all()}

    # Une relecture ne recalcule rien.
    auth_client(teo).get(f"/api/tier-lists/{tier_list.pk}/ranking")
    tier_list.refresh_from_db()
    assert {s.item_id: s.algorithm_rank for s in tier_list.scores.all()} == algorithm_ranks
    assert tier_list.scores.count() == 3


def test_un_item_sans_reponse_reste_classe(teo, make_tier_list, add_items, add_valid_questions):
    """Robustesse : un item orphelin ne doit pas disparaître du classement."""
    from tierlists.services.ranking import build_ranking

    tier_list = make_tier_list(teo)
    items = add_items(tier_list, ["Seul"])
    add_valid_questions(tier_list)
    build_ranking(tier_list)
    assert tier_list.scores.count() == 1
    assert tier_list.scores.get(item=items[0]).current_rank == 1


def test_tous_les_scores_egaux_placent_tout_en_s(auth_client, teo, laura, played):
    """Spec §30 : cas extrême couvert de bout en bout."""
    tier_list, *_ = played
    complete_questionnaire(auth_client(teo), tier_list, value=5)
    complete_questionnaire(auth_client(laura), tier_list, value=5)

    response = auth_client(teo).get(f"/api/tier-lists/{tier_list.pk}/ranking").data
    assert len(response["ranks"][0]["items"]) == 3
    assert all(len(rank["items"]) == 0 for rank in response["ranks"][1:])


def test_les_reponses_restent_invisibles_tant_que_tout_le_monde_n_a_pas_fini(
    auth_client, teo, laura, played
):
    tier_list, items, _ = played
    complete_questionnaire(auth_client(teo), tier_list, value=9)

    # Laura n'a pas fini : aucun résultat ne doit filtrer.
    for url in (
        f"/api/tier-lists/{tier_list.pk}/ranking",
        f"/api/tier-lists/{tier_list.pk}/items/{items[0].pk}/result-detail",
        f"/api/tier-lists/{tier_list.pk}/joker",
    ):
        assert auth_client(laura).get(url).status_code == 409
    assert Answer.objects.filter(participant__tier_list=tier_list).exists()
