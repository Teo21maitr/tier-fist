"""Restitution du classement et du détail d'un item (spec §31, §32).

Ces données ne sont exposées qu'à partir du statut JOKER : avant cela, aucun
résultat même provisoire ne doit sortir de l'API (spec §26).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from tierlists.constants import RANK_COLORS, RANK_NUMBERS, TierListStatus

DISPLAY_QUANTUM = Decimal("0.01")


def display_score(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(Decimal(value).quantize(DISPLAY_QUANTUM, rounding=ROUND_HALF_UP))


def ranking_payload(tier_list, request=None) -> dict:
    """Les cinq rangs et leurs items, triés par score décroissant (spec §27.7)."""
    from tierlists.models import ItemScore
    from tierlists.serializers import ItemSerializer

    scores = (
        ItemScore.objects.filter(tier_list=tier_list)
        .select_related("item")
        .order_by("-global_score", "item_id")
    )

    buckets: dict[int, list] = {number: [] for number in RANK_NUMBERS}
    for score in scores:
        payload = ItemSerializer(score.item, context={"request": request}).data
        payload["global_score"] = display_score(score.global_score)
        payload["algorithm_rank"] = score.algorithm_rank
        payload["moved_by_joker"] = score.algorithm_rank != score.current_rank
        buckets[score.current_rank].append(payload)

    return {
        "status": tier_list.status,
        "is_final": tier_list.status == TierListStatus.COMPLETED,
        "ranks": [
            {
                "number": number,
                "name": tier_list.rank_name(number),
                "color": RANK_COLORS[index],
                "items": buckets[number],
            }
            for index, number in enumerate(RANK_NUMBERS)
        ],
    }


def item_result_detail(tier_list, item, request=None) -> dict:
    """Score collectif, moyenne par question et détail individuel (spec §32).

    La confidentialité des réponses ne vaut que pendant la phase de réponses :
    une fois le classement produit, les participants peuvent tout consulter.
    """
    from accounts.serializers import PublicUserSerializer
    from tierlists.constants import COEFFICIENT_TOTAL
    from tierlists.models import Answer, ItemScore
    from tierlists.serializers import ItemSerializer

    questions = list(tier_list.questions.all().order_by("display_order", "id"))
    participants = list(tier_list.participants.select_related("user").order_by("joined_at", "id"))
    answers = Answer.objects.filter(item=item, participant__tier_list=tier_list).values(
        "participant_id", "question_id", "value"
    )

    by_participant: dict[int, dict[int, int]] = {}
    for row in answers:
        by_participant.setdefault(row["participant_id"], {})[row["question_id"]] = row["value"]

    question_rows = []
    for question in questions:
        values = [
            answers_for_participant[question.pk]
            for answers_for_participant in by_participant.values()
            if question.pk in answers_for_participant
        ]
        average = Decimal(sum(values)) / Decimal(len(values)) if values else None
        question_rows.append(
            {
                "id": question.pk,
                "text": question.text,
                "coefficient": question.coefficient,
                "average": display_score(average),
            }
        )

    participant_rows = []
    for participant in participants:
        values = by_participant.get(participant.pk, {})
        weighted = sum(
            values.get(question.pk, 0) * question.coefficient for question in questions
        )
        complete = len(values) == len(questions)
        individual = Decimal(weighted) / Decimal(COEFFICIENT_TOTAL) if complete else None
        participant_rows.append(
            {
                "participant_id": participant.pk,
                "user": PublicUserSerializer(participant.user, context={"request": request}).data,
                "score": display_score(individual),
                "answers": {str(question.pk): values.get(question.pk) for question in questions},
            }
        )

    score = ItemScore.objects.filter(tier_list=tier_list, item=item).first()
    return {
        "item": ItemSerializer(item, context={"request": request}).data,
        "global_score": display_score(score.global_score) if score else None,
        "current_rank": score.current_rank if score else None,
        "algorithm_rank": score.algorithm_rank if score else None,
        "rank_name": tier_list.rank_name(score.current_rank) if score else None,
        "questions": question_rows,
        "participants": participant_rows,
    }
