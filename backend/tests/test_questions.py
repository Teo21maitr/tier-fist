"""Questions et distribution imposée des coefficients (spec §15, §16, §52, §60)."""

from __future__ import annotations

import pytest

from tierlists.constants import TierListStatus
from tierlists.models import Question
from tierlists.services.structure import available_coefficients

pytestmark = pytest.mark.django_db

TEXT = "Cet item est visuellement réussi."


def create_question(client, tier_list, coefficient, text=TEXT):
    return client.post(
        f"/api/tier-lists/{tier_list.pk}/questions",
        {"text": text, "coefficient": coefficient},
        format="json",
    )


def test_creation_d_une_question(auth_client, teo, make_tier_list):
    tier_list = make_tier_list(teo)
    response = create_question(auth_client(teo), tier_list, 5)
    assert response.status_code == 201
    assert response.data["coefficient"] == 5


def test_coefficient_invalide_refuse(auth_client, teo, make_tier_list):
    tier_list = make_tier_list(teo)
    assert create_question(auth_client(teo), tier_list, 4).status_code == 400


def test_coefficients_disponibles(auth_client, teo, make_tier_list):
    """Spec §15.1 : si 1, 1, 2, 5 sont pris, seuls 2 et 3 restent."""
    tier_list = make_tier_list(teo)
    client = auth_client(teo)
    for coefficient in (1, 1, 2, 5):
        create_question(client, tier_list, coefficient, f"Question {coefficient}.")
    assert available_coefficients(tier_list) == [2, 3]


def test_le_coefficient_5_ne_peut_etre_pris_qu_une_fois(auth_client, teo, make_tier_list):
    tier_list = make_tier_list(teo)
    client = auth_client(teo)
    create_question(client, tier_list, 5, "Première.")
    response = create_question(client, tier_list, 5, "Deuxième.")
    assert response.status_code == 400
    assert "qu'un patron" in str(response.data)


@pytest.mark.parametrize("coefficient,slots", [(1, 2), (2, 2), (3, 1), (5, 1)])
def test_chaque_coefficient_a_son_quota(auth_client, teo, make_tier_list, coefficient, slots):
    tier_list = make_tier_list(teo)
    client = auth_client(teo)
    for index in range(slots):
        assert create_question(
            client, tier_list, coefficient, f"Cet item est réussi ({index})."
        ).status_code == 201
    assert create_question(client, tier_list, coefficient, "Une de trop.").status_code == 400


def test_pas_de_septieme_question(auth_client, teo, make_tier_list, add_valid_questions):
    tier_list = make_tier_list(teo)
    add_valid_questions(tier_list)
    response = create_question(auth_client(teo), tier_list, 1, "La septième.")
    assert response.status_code == 409
    assert response.data["code"] == "too_many_questions"


def test_modification_d_une_question(auth_client, teo, make_tier_list):
    tier_list = make_tier_list(teo)
    client = auth_client(teo)
    created = create_question(client, tier_list, 1, "Ancienne formulation.")
    response = client.patch(
        f"/api/tier-lists/{tier_list.pk}/questions/{created.data['id']}",
        {"text": "Nouvelle formulation plus claire."},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["text"] == "Nouvelle formulation plus claire."


def test_une_question_peut_garder_son_propre_coefficient(auth_client, teo, make_tier_list):
    """Modifier une question sans changer son coefficient ne doit pas se bloquer soi-même."""
    tier_list = make_tier_list(teo)
    client = auth_client(teo)
    created = create_question(client, tier_list, 5, "Question phare.")
    response = client.patch(
        f"/api/tier-lists/{tier_list.pk}/questions/{created.data['id']}",
        {"text": "Question phare révisée.", "coefficient": 5},
        format="json",
    )
    assert response.status_code == 200


def test_changer_pour_un_coefficient_pris_est_refuse(auth_client, teo, make_tier_list):
    tier_list = make_tier_list(teo)
    client = auth_client(teo)
    create_question(client, tier_list, 5, "Phare.")
    second = create_question(client, tier_list, 3, "Secondaire.")
    response = client.patch(
        f"/api/tier-lists/{tier_list.pk}/questions/{second.data['id']}",
        {"coefficient": 5},
        format="json",
    )
    assert response.status_code == 400


def test_suppression_libere_le_coefficient(auth_client, teo, make_tier_list):
    tier_list = make_tier_list(teo)
    client = auth_client(teo)
    created = create_question(client, tier_list, 5, "Phare.")
    client.delete(f"/api/tier-lists/{tier_list.pk}/questions/{created.data['id']}")
    assert available_coefficients(tier_list) == [1, 2, 3, 5]
    assert create_question(client, tier_list, 5, "Nouvelle phare.").status_code == 201


def test_texte_trop_court_refuse(auth_client, teo, make_tier_list):
    tier_list = make_tier_list(teo)
    assert create_question(auth_client(teo), tier_list, 1, "Non").status_code == 400


def test_tout_participant_peut_creer_une_question(auth_client, teo, laura, make_tier_list, join):
    tier_list = make_tier_list(teo)
    join(tier_list, laura)
    assert create_question(auth_client(laura), tier_list, 3).status_code == 201


def test_questions_figees_apres_finalisation(auth_client, teo, make_tier_list, add_valid_questions):
    tier_list = make_tier_list(teo)
    questions = add_valid_questions(tier_list)
    tier_list.status = TierListStatus.ANSWERING
    tier_list.save()
    client = auth_client(teo)

    assert create_question(client, tier_list, 1).status_code == 409
    assert client.patch(
        f"/api/tier-lists/{tier_list.pk}/questions/{questions[0].pk}",
        {"text": "Changement interdit."},
        format="json",
    ).status_code == 409
    assert client.delete(
        f"/api/tier-lists/{tier_list.pk}/questions/{questions[0].pk}"
    ).status_code == 409


def test_le_coefficient_est_masque_pendant_le_questionnaire(
    auth_client, teo, make_tier_list, add_valid_questions
):
    """Spec §15.3 : coefficient visible en DRAFT, caché pendant le questionnaire."""
    tier_list = make_tier_list(teo)
    add_valid_questions(tier_list)
    client = auth_client(teo)

    draft = client.get(f"/api/tier-lists/{tier_list.pk}/questions")
    assert "coefficient" in draft.data[0]

    tier_list.status = TierListStatus.ANSWERING
    tier_list.save()
    answering = client.get(f"/api/tier-lists/{tier_list.pk}/questions")
    assert "coefficient" not in answering.data[0]


def test_concurrence_sur_le_dernier_coefficient_5(teo, laura, make_tier_list, join):
    """Deux créations simultanées du coefficient 5 : une seule doit réussir (spec §52)."""
    from rest_framework.test import APIClient

    tier_list = make_tier_list(teo)
    join(tier_list, laura)

    results = []
    for user in (teo, laura):
        client = APIClient()
        client.force_authenticate(user=user)
        results.append(create_question(client, tier_list, 5, f"Phare de {user.username}.").status_code)

    assert sorted(results) == [201, 400]
    assert Question.objects.filter(tier_list=tier_list, coefficient=5).count() == 1
