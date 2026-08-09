"""Phase joker : ordre, déplacement, verrouillage, skip, force-skip (spec §33 à §40)."""

from __future__ import annotations

import pytest

from tests.helpers import complete_questionnaire
from tierlists.constants import JokerStatus, TierListStatus
from tierlists.models import Item, JokerAction

pytestmark = pytest.mark.django_db


@pytest.fixture
def joker_phase(auth_client, teo, laura, paul, join, make_tier_list, add_items, add_valid_questions):
    """Partie à 3 joueurs, en phase JOKER.

    Ordre de complétion : teo, puis laura, puis paul.
    L'ordre des jokers est donc l'inverse : paul, laura, teo (spec §34).

    Cinq items avec cinq scores distincts : la répartition remplit exactement
    les cinq rangs (S1/A1/B1/C1/D1), ce qui permet de tester un vrai D -> S.
    """
    tier_list = make_tier_list(teo)
    join(tier_list, laura)
    join(tier_list, paul)
    items = add_items(tier_list, ["KFC", "Quick", "McDo", "Burger King", "Subway"])
    add_valid_questions(tier_list)
    auth_client(teo).post(f"/api/tier-lists/{tier_list.pk}/finalize")

    per_item = {
        items[0].pk: 9,
        items[1].pk: 7,
        items[2].pk: 5,
        items[3].pk: 3,
        items[4].pk: 1,
    }
    for user in (teo, laura, paul):
        complete_questionnaire(auth_client(user), tier_list, per_item=per_item)

    tier_list.refresh_from_db()
    assert tier_list.status == TierListStatus.JOKER
    return tier_list, items


# ---------------------------------------------------------------------------
# Ordre des tours
# ---------------------------------------------------------------------------


def test_l_ordre_des_jokers_est_l_inverse_de_l_ordre_de_completion(
    auth_client, teo, joker_phase
):
    tier_list, _items = joker_phase
    state = auth_client(teo).get(f"/api/tier-lists/{tier_list.pk}/joker").data
    assert [row["user"]["username"] for row in state["order"]] == ["paul", "laura", "teo"]
    assert state["current_turn"]["user"]["username"] == "paul"


def test_celui_qui_finit_en_premier_joue_en_dernier(auth_client, teo, joker_phase):
    tier_list, _items = joker_phase
    state = auth_client(teo).get(f"/api/tier-lists/{tier_list.pk}/joker").data
    assert state["is_my_turn"] is False
    assert state["my_joker"]["joker_order"] == 3


def test_un_joueur_hors_tour_ne_peut_pas_jouer(auth_client, teo, joker_phase):
    tier_list, items = joker_phase
    response = auth_client(teo).post(
        f"/api/tier-lists/{tier_list.pk}/joker/use",
        {"item_id": items[0].pk, "to_rank": 5},
        format="json",
    )
    assert response.status_code == 403
    assert response.data["code"] == "not_your_turn"


def test_le_tour_avance_apres_chaque_joker(auth_client, paul, laura, joker_phase):
    tier_list, _items = joker_phase
    auth_client(paul).post(f"/api/tier-lists/{tier_list.pk}/joker/skip")
    state = auth_client(laura).get(f"/api/tier-lists/{tier_list.pk}/joker").data
    assert state["current_turn"]["user"]["username"] == "laura"
    assert state["is_my_turn"] is True


# ---------------------------------------------------------------------------
# Utilisation du joker
# ---------------------------------------------------------------------------


def test_deplacement_d_vers_s(auth_client, paul, joker_phase):
    """Spec §33 : D -> S est explicitement autorisé."""
    tier_list, items = joker_phase
    dernier = items[4]  # Subway, noté 1 : rang le plus bas
    score = tier_list.scores.get(item=dernier)
    assert score.current_rank == 5

    response = auth_client(paul).post(
        f"/api/tier-lists/{tier_list.pk}/joker/use",
        {"item_id": dernier.pk, "to_rank": 1},
        format="json",
    )
    assert response.status_code == 200
    score.refresh_from_db()
    assert score.current_rank == 1
    # Le rang issu de l'algorithme ne change jamais.
    assert score.algorithm_rank == 5


def test_le_joker_ne_modifie_ni_le_score_ni_les_reponses(auth_client, paul, joker_phase):
    tier_list, items = joker_phase
    score_avant = tier_list.scores.get(item=items[4]).global_score
    auth_client(paul).post(
        f"/api/tier-lists/{tier_list.pk}/joker/use",
        {"item_id": items[4].pk, "to_rank": 1},
        format="json",
    )
    assert tier_list.scores.get(item=items[4]).global_score == score_avant


def test_un_item_deplace_est_verrouille(auth_client, paul, laura, joker_phase):
    """Spec §36 : un item ne subit qu'un seul joker sur toute la partie."""
    tier_list, items = joker_phase
    auth_client(paul).post(
        f"/api/tier-lists/{tier_list.pk}/joker/use",
        {"item_id": items[0].pk, "to_rank": 5},
        format="json",
    )
    items[0].refresh_from_db()
    assert items[0].joker_locked is True

    response = auth_client(laura).post(
        f"/api/tier-lists/{tier_list.pk}/joker/use",
        {"item_id": items[0].pk, "to_rank": 1},
        format="json",
    )
    assert response.status_code == 409
    assert response.data["code"] == "item_joker_locked"


def test_deplacer_vers_le_meme_rang_est_refuse(auth_client, paul, joker_phase):
    tier_list, items = joker_phase
    rank = tier_list.scores.get(item=items[0]).current_rank
    response = auth_client(paul).post(
        f"/api/tier-lists/{tier_list.pk}/joker/use",
        {"item_id": items[0].pk, "to_rank": rank},
        format="json",
    )
    assert response.status_code == 400
    assert response.data["code"] == "same_rank"


def test_rang_invalide_refuse(auth_client, paul, joker_phase):
    tier_list, items = joker_phase
    response = auth_client(paul).post(
        f"/api/tier-lists/{tier_list.pk}/joker/use",
        {"item_id": items[0].pk, "to_rank": 7},
        format="json",
    )
    assert response.status_code == 400


def test_item_d_une_autre_tier_list_refuse(auth_client, paul, joker_phase, make_tier_list, add_items):
    tier_list, _items = joker_phase
    autre = make_tier_list(paul, name="Autre")
    (intrus,) = add_items(autre, ["Intrus"])
    response = auth_client(paul).post(
        f"/api/tier-lists/{tier_list.pk}/joker/use",
        {"item_id": intrus.pk, "to_rank": 1},
        format="json",
    )
    assert response.status_code == 400
    assert response.data["code"] == "unknown_item"


def test_un_joueur_ne_joue_qu_une_seule_fois(auth_client, paul, joker_phase):
    tier_list, items = joker_phase
    client = auth_client(paul)
    client.post(
        f"/api/tier-lists/{tier_list.pk}/joker/use",
        {"item_id": items[0].pk, "to_rank": 5},
        format="json",
    )
    response = client.post(
        f"/api/tier-lists/{tier_list.pk}/joker/use",
        {"item_id": items[1].pk, "to_rank": 1},
        format="json",
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Visibilité de l'historique (spec §35)
# ---------------------------------------------------------------------------


def test_l_historique_montre_qui_a_deplace_quoi(auth_client, paul, laura, joker_phase):
    tier_list, items = joker_phase
    auth_client(paul).post(
        f"/api/tier-lists/{tier_list.pk}/joker/use",
        {"item_id": items[4].pk, "to_rank": 1},
        format="json",
    )
    state = auth_client(laura).get(f"/api/tier-lists/{tier_list.pk}/joker").data
    entry = state["history"][0]
    assert entry["user"]["username"] == "paul"
    assert entry["item"]["name"] == "Subway"
    assert entry["from_rank"] == 5
    assert entry["to_rank"] == 1
    assert state["locked_item_ids"] == [items[4].pk]


# ---------------------------------------------------------------------------
# Abandon et forçage
# ---------------------------------------------------------------------------


def test_abandon_du_joker(auth_client, paul, joker_phase):
    tier_list, _items = joker_phase
    response = auth_client(paul).post(f"/api/tier-lists/{tier_list.pk}/joker/skip")
    assert response.status_code == 200
    action = JokerAction.objects.get(participant__user=paul, tier_list=tier_list)
    assert action.status == JokerStatus.SKIPPED
    assert not Item.objects.filter(tier_list=tier_list, joker_locked=True).exists()


def test_seul_le_createur_peut_forcer_un_tour(auth_client, laura, joker_phase):
    tier_list, _items = joker_phase
    response = auth_client(laura).post(f"/api/tier-lists/{tier_list.pk}/joker/force-skip")
    assert response.status_code == 403
    assert response.data["code"] == "not_creator"


def test_le_createur_force_le_tour_du_joueur_actif(auth_client, teo, paul, joker_phase):
    tier_list, _items = joker_phase
    response = auth_client(teo).post(f"/api/tier-lists/{tier_list.pk}/joker/force-skip")
    assert response.status_code == 200

    action = JokerAction.objects.get(participant__user=paul, tier_list=tier_list)
    assert action.status == JokerStatus.FORCED_SKIP
    assert action.forced_by == teo
    # Le tour passe immédiatement au joueur suivant.
    assert response.data["current_turn"]["user"]["username"] == "laura"


def test_le_force_skip_apparait_dans_l_historique(auth_client, teo, joker_phase):
    tier_list, _items = joker_phase
    auth_client(teo).post(f"/api/tier-lists/{tier_list.pk}/joker/force-skip")
    state = auth_client(teo).get(f"/api/tier-lists/{tier_list.pk}/joker").data
    assert state["history"][0]["status"] == JokerStatus.FORCED_SKIP


# ---------------------------------------------------------------------------
# Fin de partie
# ---------------------------------------------------------------------------


def test_la_partie_se_termine_quand_tous_les_jokers_sont_joues(
    auth_client, teo, laura, paul, joker_phase
):
    tier_list, items = joker_phase
    auth_client(paul).post(
        f"/api/tier-lists/{tier_list.pk}/joker/use",
        {"item_id": items[4].pk, "to_rank": 1},
        format="json",
    )
    auth_client(laura).post(f"/api/tier-lists/{tier_list.pk}/joker/skip")
    tier_list.refresh_from_db()
    assert tier_list.status == TierListStatus.JOKER

    auth_client(teo).post(f"/api/tier-lists/{tier_list.pk}/joker/skip")
    tier_list.refresh_from_db()
    assert tier_list.status == TierListStatus.COMPLETED
    assert tier_list.completed_at is not None

    # Le classement courant devient définitif.
    for score in tier_list.scores.all():
        assert score.final_rank == score.current_rank


def test_plus_aucun_joker_apres_la_fin(auth_client, teo, laura, paul, joker_phase):
    tier_list, items = joker_phase
    for user in (paul, laura, teo):
        auth_client(user).post(f"/api/tier-lists/{tier_list.pk}/joker/skip")

    response = auth_client(teo).post(
        f"/api/tier-lists/{tier_list.pk}/joker/use",
        {"item_id": items[0].pk, "to_rank": 1},
        format="json",
    )
    assert response.status_code == 409
    assert response.data["code"] == "not_joker_phase"


def test_le_resultat_reste_consultable_apres_la_fin(auth_client, teo, laura, paul, joker_phase):
    tier_list, _items = joker_phase
    for user in (paul, laura, teo):
        auth_client(user).post(f"/api/tier-lists/{tier_list.pk}/joker/skip")

    response = auth_client(teo).get(f"/api/tier-lists/{tier_list.pk}/ranking")
    assert response.status_code == 200
    assert response.data["is_final"] is True


def test_deux_requetes_concurrentes_ne_consomment_qu_un_tour(teo, laura, paul, joker_phase):
    """Spec §52 : une seule opération doit réussir sur le même tour."""
    from rest_framework.test import APIClient

    tier_list, items = joker_phase
    statuses = []
    for target_rank in (1, 2):
        client = APIClient()
        client.force_authenticate(user=paul)
        statuses.append(
            client.post(
                f"/api/tier-lists/{tier_list.pk}/joker/use",
                {"item_id": items[4].pk, "to_rank": target_rank},
                format="json",
            ).status_code
        )

    assert statuses[0] == 200
    # La deuxième requête est rejetée : le tour est déjà consommé.
    assert statuses[1] in (403, 409)
    assert JokerAction.objects.filter(
        tier_list=tier_list, status=JokerStatus.USED
    ).count() == 1


def test_un_non_participant_ne_voit_pas_la_phase_joker(auth_client, make_user, joker_phase):
    tier_list, _items = joker_phase
    intrus = make_user("intrus")
    assert auth_client(intrus).get(f"/api/tier-lists/{tier_list.pk}/joker").status_code == 404
