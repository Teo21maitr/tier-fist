"""Tier List privée, code d'invitation, join, permissions (spec §9 à §13, §50)."""

from __future__ import annotations

import pytest

from tierlists.constants import INVITE_CODE_LENGTH, TierListStatus
from tierlists.models import TierList, TierListParticipant

pytestmark = pytest.mark.django_db


def test_creation_ajoute_le_createur_comme_participant(auth_client, teo):
    response = auth_client(teo).post(
        "/api/tier-lists", {"name": "Meilleurs fast-foods", "theme": "Fast-food"}, format="json"
    )
    assert response.status_code == 201
    tier_list = TierList.objects.get(pk=response.data["id"])
    assert tier_list.creator == teo
    assert tier_list.participants.filter(user=teo).exists()
    assert tier_list.status == TierListStatus.DRAFT


def test_le_code_d_invitation_respecte_le_format(auth_client, teo):
    response = auth_client(teo).post(
        "/api/tier-lists", {"name": "Pokémon", "theme": "Jeux"}, format="json"
    )
    code = response.data["invite_code"]
    assert len(code) == INVITE_CODE_LENGTH
    assert code.isalnum() and code.isupper()
    # Caractères ambigus exclus (spec §9.1).
    assert not set(code) & set("01OI")


def test_les_codes_sont_uniques(auth_client, teo):
    client = auth_client(teo)
    codes = {
        client.post("/api/tier-lists", {"name": f"L{i}", "theme": "T"}, format="json").data[
            "invite_code"
        ]
        for i in range(25)
    }
    assert len(codes) == 25


def test_les_rangs_par_defaut_sont_s_a_b_c_d(auth_client, teo):
    response = auth_client(teo).post(
        "/api/tier-lists", {"name": "X", "theme": "Y"}, format="json"
    )
    assert [rank["name"] for rank in response.data["ranks"]] == ["S", "A", "B", "C", "D"]
    assert [rank["color"] for rank in response.data["ranks"]] == [
        "red",
        "orange",
        "yellow",
        "green",
        "blue",
    ]


def test_nom_et_theme_obligatoires(auth_client, teo):
    assert auth_client(teo).post("/api/tier-lists", {"name": " ", "theme": " "}, format="json").status_code == 400


# --- Confidentialité --------------------------------------------------------


def test_un_non_participant_ne_voit_pas_la_tier_list(auth_client, teo, laura, make_tier_list):
    tier_list = make_tier_list(teo)
    # 404 et non 403 : l'existence même ne doit pas être confirmée (spec §51).
    assert auth_client(laura).get(f"/api/tier-lists/{tier_list.pk}").status_code == 404


def test_un_non_participant_ne_peut_pas_lister_ses_items(auth_client, teo, laura, make_tier_list):
    tier_list = make_tier_list(teo)
    assert auth_client(laura).get(f"/api/tier-lists/{tier_list.pk}/items").status_code == 404


def test_la_liste_ne_contient_que_mes_tier_lists(auth_client, teo, laura, make_tier_list):
    make_tier_list(teo, name="A")
    make_tier_list(laura, name="B")
    response = auth_client(teo).get("/api/tier-lists")
    assert [item["name"] for item in response.data] == ["A"]


def test_anonyme_refuse(api, teo, make_tier_list):
    tier_list = make_tier_list(teo)
    assert api.get(f"/api/tier-lists/{tier_list.pk}").status_code == 403


# --- Join -------------------------------------------------------------------


def test_join_avec_un_code_valide(auth_client, teo, laura, make_tier_list):
    tier_list = make_tier_list(teo)
    response = auth_client(laura).post(
        "/api/tier-lists/join", {"code": tier_list.invite_code}, format="json"
    )
    assert response.status_code == 201
    assert response.data["already_member"] is False
    assert tier_list.participants.filter(user=laura).exists()


def test_join_insensible_a_la_casse_et_aux_espaces(auth_client, teo, laura, make_tier_list):
    tier_list = make_tier_list(teo)
    response = auth_client(laura).post(
        "/api/tier-lists/join", {"code": f" {tier_list.invite_code.lower()} "}, format="json"
    )
    assert response.status_code == 201


def test_join_deux_fois_ne_cree_pas_de_doublon(auth_client, teo, laura, make_tier_list):
    tier_list = make_tier_list(teo)
    client = auth_client(laura)
    client.post("/api/tier-lists/join", {"code": tier_list.invite_code}, format="json")
    response = client.post("/api/tier-lists/join", {"code": tier_list.invite_code}, format="json")
    assert response.status_code == 200
    assert response.data["already_member"] is True
    assert TierListParticipant.objects.filter(tier_list=tier_list, user=laura).count() == 1


def test_join_avec_un_code_inconnu(auth_client, laura):
    response = auth_client(laura).post("/api/tier-lists/join", {"code": "ZZZZZZ"}, format="json")
    assert response.status_code == 404
    assert response.data["code"] == "unknown_code"


def test_join_impossible_apres_finalisation(auth_client, teo, laura, make_tier_list):
    tier_list = make_tier_list(teo)
    tier_list.status = TierListStatus.ANSWERING
    tier_list.save()
    response = auth_client(laura).post(
        "/api/tier-lists/join", {"code": tier_list.invite_code}, format="json"
    )
    assert response.status_code == 409
    assert response.data["code"] == "already_finalized"


def test_le_createur_qui_rejoint_son_propre_code_reste_unique(auth_client, teo, make_tier_list):
    tier_list = make_tier_list(teo)
    response = auth_client(teo).post(
        "/api/tier-lists/join", {"code": tier_list.invite_code}, format="json"
    )
    assert response.data["already_member"] is True


# --- Rangs et édition -------------------------------------------------------


def test_tout_participant_peut_renommer_les_rangs(auth_client, teo, laura, make_tier_list, join):
    tier_list = make_tier_list(teo)
    join(tier_list, laura)
    response = auth_client(laura).patch(
        f"/api/tier-lists/{tier_list.pk}",
        {"rank_1_name": "Légendaire", "rank_5_name": "Poubelle"},
        format="json",
    )
    assert response.status_code == 200
    tier_list.refresh_from_db()
    assert tier_list.rank_1_name == "Légendaire"
    assert tier_list.rank_5_name == "Poubelle"


def test_un_nom_de_rang_vide_est_refuse(auth_client, teo, make_tier_list):
    tier_list = make_tier_list(teo)
    response = auth_client(teo).patch(
        f"/api/tier-lists/{tier_list.pk}", {"rank_1_name": "  "}, format="json"
    )
    assert response.status_code == 400


def test_renommage_impossible_apres_finalisation(auth_client, teo, make_tier_list):
    tier_list = make_tier_list(teo)
    tier_list.status = TierListStatus.ANSWERING
    tier_list.save()
    response = auth_client(teo).patch(
        f"/api/tier-lists/{tier_list.pk}", {"rank_1_name": "Nope"}, format="json"
    )
    assert response.status_code == 409
    assert response.data["code"] == "structure_frozen"


# --- Suppression ------------------------------------------------------------


def test_seul_le_createur_peut_supprimer(auth_client, teo, laura, make_tier_list, join):
    tier_list = make_tier_list(teo)
    join(tier_list, laura)
    assert auth_client(laura).delete(f"/api/tier-lists/{tier_list.pk}").status_code == 403
    assert auth_client(teo).delete(f"/api/tier-lists/{tier_list.pk}").status_code == 204
    assert not TierList.objects.filter(pk=tier_list.pk).exists()


def test_suppression_possible_meme_terminee(auth_client, teo, make_tier_list):
    tier_list = make_tier_list(teo, status=TierListStatus.COMPLETED)
    assert auth_client(teo).delete(f"/api/tier-lists/{tier_list.pk}").status_code == 204


def test_la_suppression_emporte_les_donnees_liees(
    auth_client, teo, make_tier_list, add_items, add_valid_questions
):
    from tierlists.models import Item, Question

    tier_list = make_tier_list(teo)
    add_items(tier_list, ["KFC"])
    add_valid_questions(tier_list)
    auth_client(teo).delete(f"/api/tier-lists/{tier_list.pk}")
    assert not Item.objects.filter(tier_list_id=tier_list.pk).exists()
    assert not Question.objects.filter(tier_list_id=tier_list.pk).exists()
    assert not TierListParticipant.objects.filter(tier_list_id=tier_list.pk).exists()


# --- Participants -----------------------------------------------------------


def test_liste_des_participants(auth_client, teo, laura, make_tier_list, join):
    tier_list = make_tier_list(teo)
    join(tier_list, laura)
    response = auth_client(teo).get(f"/api/tier-lists/{tier_list.pk}/participants")
    assert response.status_code == 200
    usernames = sorted(row["user"]["username"] for row in response.data)
    assert usernames == ["laura", "teo"]
