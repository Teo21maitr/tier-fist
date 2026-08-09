"""Helpers de scénario : jouer une partie complète depuis les tests."""

from __future__ import annotations

from tierlists.models import Answer, ParticipantItemProgress, Question


def answer_item(client, tier_list, item_id, values: dict[int, int]):
    """Envoie une réponse par question puis valide l'item."""
    for question_id, value in values.items():
        response = client.put(
            f"/api/tier-lists/{tier_list.pk}/items/{item_id}/answers/{question_id}",
            {"value": value},
            format="json",
        )
        assert response.status_code == 200, response.data
    return client.post(f"/api/tier-lists/{tier_list.pk}/items/{item_id}/validate")


def complete_questionnaire(client, tier_list, value: int = 5, per_item: dict | None = None):
    """Répond à tout le questionnaire d'un participant.

    ``per_item`` permet de forcer la valeur donnée à un item : ``{item_id: valeur}``.
    """
    questions = list(Question.objects.filter(tier_list=tier_list).values_list("id", flat=True))
    answering = client.get(f"/api/tier-lists/{tier_list.pk}/answering")
    assert answering.status_code == 200, answering.data

    last = None
    for item in answering.data["items"]:
        if item["is_validated"]:
            continue  # déjà verrouillé : on ne peut plus y toucher
        item_value = (per_item or {}).get(item["id"], value)
        last = answer_item(
            client, tier_list, item["id"], {qid: item_value for qid in questions}
        )
        assert last.status_code == 200, last.data
    return last


def set_answers_directly(participant, item, value: int, validated: bool = True):
    """Écrit les réponses en base sans passer par l'API (mise en place rapide)."""
    tier_list = participant.tier_list
    for question in Question.objects.filter(tier_list=tier_list):
        Answer.objects.update_or_create(
            participant=participant, item=item, question=question, defaults={"value": value}
        )
    if validated:
        progress = ParticipantItemProgress.objects.get(participant=participant, item=item)
        progress.validate()
