"""Progression des participants (spec §21, §22).

On expose uniquement un pourcentage et un statut terminé/non terminé : jamais
les valeurs de réponse, jamais une moyenne, jamais un classement provisoire.
"""

from __future__ import annotations

from django.db.models import Count, Q


def _percent(validated: int, total: int) -> int:
    if total <= 0:
        return 0
    return round(validated * 100 / total)


def participant_progress(participant) -> dict:
    from tierlists.models import ParticipantItemProgress

    rows = ParticipantItemProgress.objects.filter(participant=participant).aggregate(
        total=Count("id"), validated=Count("id", filter=Q(is_validated=True))
    )
    total = rows["total"] or 0
    validated = rows["validated"] or 0
    return {
        "validated_items": validated,
        "total_items": total,
        "progress_percent": _percent(validated, total),
        "has_finished": participant.answering_completed_at is not None,
    }


def all_participants_progress(tier_list, request=None) -> list[dict]:
    """Avancement de tous les participants, en une seule requête agrégée."""
    from accounts.serializers import PublicUserSerializer

    participants = (
        tier_list.participants.select_related("user")
        .annotate(
            total=Count("item_progress"),
            validated=Count("item_progress", filter=Q(item_progress__is_validated=True)),
        )
        .order_by("joined_at", "id")
    )
    return [
        {
            "id": participant.pk,
            "user": PublicUserSerializer(participant.user, context={"request": request}).data,
            "is_creator": participant.user_id == tier_list.creator_id,
            "validated_items": participant.validated,
            "total_items": participant.total,
            "progress_percent": _percent(participant.validated, participant.total),
            "has_finished": participant.answering_completed_at is not None,
        }
        for participant in participants
    ]
