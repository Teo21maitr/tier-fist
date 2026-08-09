"""Scénario de recette fonctionnelle de bout en bout (spec §71).

Ce test rejoue les 29 étapes vérifiables côté applicatif du scénario d'acceptation.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from accounts.models import User
from tierlists.constants import TierListStatus
from tierlists.models import Answer, JokerAction, Question, TierList

pytestmark = pytest.mark.django_db


def register_and_approve(api, username: str, password: str = "MotDePasse!42") -> User:
    assert api.post(
        "/api/auth/register", {"username": username, "password": password}, format="json"
    ).status_code == 201
    user = User.objects.get(username=username)
    assert not user.is_active  # étape 2 : le compte apparaît pending
    user.approve()  # étape 3 : l'admin l'accepte
    return user


def login(username: str, password: str = "MotDePasse!42") -> APIClient:
    client = APIClient()
    assert client.post(
        "/api/auth/login", {"username": username, "password": password}, format="json"
    ).status_code == 200
    return client


def test_scenario_de_recette_complet(api):
    # 1 à 4 — Teo crée son compte, il est validé, il se connecte.
    register_and_approve(api, "teo")
    teo_client = login("teo")

    # 5, 6 — Il crée « Fast-food » et reçoit un code d'invitation.
    created = teo_client.post(
        "/api/tier-lists", {"name": "Fast-food", "theme": "Fast-food"}, format="json"
    )
    tier_list_id = created.data["id"]
    code = created.data["invite_code"]
    assert len(code) == 6

    # 7, 8 — Laura crée son compte et rejoint avec le code.
    register_and_approve(api, "laura")
    laura_client = login("laura")
    assert laura_client.post("/api/tier-lists/join", {"code": code}, format="json").status_code == 201

    # 9 — Les deux ajoutent des items.
    for client, names in ((teo_client, ["KFC", "McDo"]), (laura_client, ["Quick", "Burger King"])):
        for name in names:
            assert client.post(
                f"/api/tier-lists/{tier_list_id}/items", {"name": name}, format="json"
            ).status_code == 201

    # 10 — Ils créent ensemble les six questions.
    plan = [(teo_client, 1), (laura_client, 1), (teo_client, 2), (laura_client, 2),
            (teo_client, 3), (laura_client, 5)]
    for index, (client, coefficient) in enumerate(plan):
        assert client.post(
            f"/api/tier-lists/{tier_list_id}/questions",
            {"text": f"Cet item est réussi sur le critère {index + 1}.", "coefficient": coefficient},
            format="json",
        ).status_code == 201

    # 11 — Ils renomment un rang.
    assert laura_client.patch(
        f"/api/tier-lists/{tier_list_id}", {"rank_1_name": "Culte"}, format="json"
    ).status_code == 200

    # 12 — Teo finalise.
    assert teo_client.post(f"/api/tier-lists/{tier_list_id}/finalize").status_code == 200

    # 13 — Plus personne ne peut rejoindre.
    register_and_approve(api, "paul")
    paul_client = login("paul")
    assert paul_client.post("/api/tier-lists/join", {"code": code}, format="json").status_code == 409

    # 14 — Chaque joueur reçoit un ordre d'items mélangé et indépendant.
    tier_list = TierList.objects.get(pk=tier_list_id)
    questions = list(Question.objects.filter(tier_list=tier_list).values_list("id", flat=True))
    orders = {}
    for name, client in (("teo", teo_client), ("laura", laura_client)):
        response = client.get(f"/api/tier-lists/{tier_list_id}/answering")
        assert response.status_code == 200
        orders[name] = [item["id"] for item in response.data["items"]]
    assert sorted(orders["teo"]) == sorted(orders["laura"])

    # 15 à 17 — Chacun répond, chaque réponse est autosauvegardée, chaque item verrouillé.
    values = {"teo": [9, 7, 5, 3], "laura": [8, 6, 4, 2]}
    for name, client in (("teo", teo_client), ("laura", laura_client)):
        item_values = dict(zip(sorted(orders[name]), values[name], strict=False))
        for item_id in orders[name]:
            for question_id in questions:
                assert client.put(
                    f"/api/tier-lists/{tier_list_id}/items/{item_id}/answers/{question_id}",
                    {"value": item_values[item_id]},
                    format="json",
                ).status_code == 200
            assert client.post(
                f"/api/tier-lists/{tier_list_id}/items/{item_id}/validate"
            ).status_code == 200
            # 17 — après validation, plus aucune modification possible.
            assert client.put(
                f"/api/tier-lists/{tier_list_id}/items/{item_id}/answers/{questions[0]}",
                {"value": 1},
                format="json",
            ).status_code == 409

        # 18 — pendant que Teo répond, on voit la progression de l'autre, pas ses notes.
        if name == "teo":
            state = teo_client.get(f"/api/tier-lists/{tier_list_id}/answering").data
            laura_row = next(p for p in state["participants"] if p["user"]["username"] == "laura")
            assert "answers" not in laura_row

    # 19 à 21 — Teo a terminé en premier, Laura ensuite ; le classement est généré.
    tier_list.refresh_from_db()
    assert tier_list.status == TierListStatus.JOKER

    # 22 — Les résultats deviennent visibles.
    ranking = teo_client.get(f"/api/tier-lists/{tier_list_id}/ranking")
    assert ranking.status_code == 200
    assert sum(len(rank["items"]) for rank in ranking.data["ranks"]) == 4
    assert ranking.data["ranks"][0]["name"] == "Culte"

    # 23 — Laura a terminé en dernier : elle joue son joker en premier (ordre inverse).
    joker_state = laura_client.get(f"/api/tier-lists/{tier_list_id}/joker").data
    assert joker_state["is_my_turn"] is True
    dernier = joker_state["ranking"]["ranks"][-2]["items"][-1]
    used = laura_client.post(
        f"/api/tier-lists/{tier_list_id}/joker/use",
        {"item_id": dernier["id"], "to_rank": 1},
        format="json",
    )
    assert used.status_code == 200

    # 24 — L'item déplacé est verrouillé.
    assert dernier["id"] in used.data["locked_item_ids"]

    # 25, 26 — Teo joue en second, le résultat devient définitif.
    assert teo_client.post(f"/api/tier-lists/{tier_list_id}/joker/skip").status_code == 200
    tier_list.refresh_from_db()
    assert tier_list.status == TierListStatus.COMPLETED
    assert teo_client.get(f"/api/tier-lists/{tier_list_id}/ranking").data["is_final"] is True

    # 27 — Les deux consultent le détail de chaque item.
    for client in (teo_client, laura_client):
        for item_id in orders["teo"]:
            detail = client.get(
                f"/api/tier-lists/{tier_list_id}/items/{item_id}/result-detail"
            )
            assert detail.status_code == 200
            assert detail.data["global_score"] is not None
            assert len(detail.data["questions"]) == 6
            assert len(detail.data["participants"]) == 2

    # 28, 29 — Teo duplique ; la copie est vierge.
    copy_response = teo_client.post(f"/api/tier-lists/{tier_list_id}/duplicate")
    assert copy_response.status_code == 201
    copy = TierList.objects.get(pk=copy_response.data["id"])
    assert copy.status == TierListStatus.DRAFT
    assert copy.items.count() == 4
    assert copy.questions.count() == 6
    assert copy.participants.count() == 1
    assert not Answer.objects.filter(participant__tier_list=copy).exists()
    assert not JokerAction.objects.filter(tier_list=copy).exists()
    assert not copy.scores.exists()
