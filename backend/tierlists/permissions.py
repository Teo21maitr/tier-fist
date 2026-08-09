"""Accès aux Tier Lists (spec §10, §50, §51).

Toutes les Tier Lists sont privées : un utilisateur n'y accède que s'il en est
participant. Les requêtes sont systématiquement filtrées par participation, de
sorte qu'une Tier List ne peut pas être découverte en incrémentant un ID — un
non-participant reçoit un 404, pas un 403 qui confirmerait l'existence.
"""

from __future__ import annotations

from rest_framework.exceptions import NotFound

from config.exceptions import BusinessError
from tierlists.constants import TierListStatus


def get_participant_tier_list(user, pk, *, lock: bool = False):
    """Renvoie la Tier List si l'utilisateur en est participant, sinon 404."""
    from tierlists.models import TierList

    queryset = TierList.objects.filter(participants__user=user)
    if lock:
        queryset = queryset.select_for_update()
    tier_list = queryset.filter(pk=pk).select_related("creator").first()
    if tier_list is None:
        raise NotFound("Cette Tier List n'existe pas, ou tu n'en fais pas partie.")
    return tier_list


def get_participant(tier_list, user):
    from tierlists.models import TierListParticipant

    participant = TierListParticipant.objects.filter(tier_list=tier_list, user=user).first()
    if participant is None:
        raise NotFound("Cette Tier List n'existe pas, ou tu n'en fais pas partie.")
    return participant


def require_creator(tier_list, user, action: str = "effectuer cette action") -> None:
    if tier_list.creator_id != user.pk:
        raise BusinessError(
            f"Seul le créateur peut {action}.", code="not_creator", status_code=403
        )


def require_draft(tier_list) -> None:
    """La structure n'est modifiable que pendant DRAFT (spec §8.2, §16)."""
    if tier_list.status != TierListStatus.DRAFT:
        raise BusinessError(
            "La Tier List est finalisée. Les règles ne bougent plus.",
            code="structure_frozen",
            status_code=409,
        )


def require_status(tier_list, *statuses, message: str, code: str) -> None:
    if tier_list.status not in statuses:
        raise BusinessError(message, code=code, status_code=409)
