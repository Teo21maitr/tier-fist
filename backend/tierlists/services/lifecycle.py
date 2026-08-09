"""Transitions de statut d'une Tier List (spec §8, §16, §17, §20, §26).

Toutes les transitions sensibles verrouillent la Tier List avec
``select_for_update()`` : deux participants peuvent agir simultanément et une
seule opération doit gagner (spec §52).
"""

from __future__ import annotations

import logging
import random

from django.db import transaction
from django.utils import timezone

from config.exceptions import BusinessError, Conflict
from tierlists.constants import (
    REQUIRED_QUESTION_COUNT,
    JokerStatus,
    TierListStatus,
)
from tierlists.services.ranking import build_ranking
from tierlists.services.structure import finalization_blockers

logger = logging.getLogger("tierfist")


@transaction.atomic
def finalize_tier_list(tier_list, user):
    """Fige la structure et bascule en ANSWERING. Seul le créateur peut finaliser."""
    from tierlists.models import TierList

    locked = TierList.objects.select_for_update().get(pk=tier_list.pk)

    if locked.creator_id != user.pk:
        raise BusinessError(
            "Seul le créateur peut finaliser la Tier List.",
            code="not_creator",
            status_code=403,
        )
    if locked.status != TierListStatus.DRAFT:
        raise Conflict("Trop tard, cette Tier List est déjà lancée.", code="already_finalized")

    blockers = finalization_blockers(locked)
    if blockers:
        raise BusinessError(
            "On ne finalise rien tant que les six questions et leurs coefficients "
            "ne sont pas impeccables. " + " ".join(blockers),
            code="finalization_blocked",
        )

    _generate_answer_orders(locked)

    locked.status = TierListStatus.ANSWERING
    locked.finalized_at = timezone.now()
    locked.save(update_fields=["status", "finalized_at", "updated_at"])
    logger.info(
        "Tier List %s finalisée par %s -> ANSWERING", locked.pk, user.username
    )
    return locked


def _generate_answer_orders(tier_list) -> None:
    """Crée l'ordre d'items propre à chaque participant (spec §17).

    Chaque participant reçoit un ordre aléatoire indépendant, dérivé de sa seed
    persistante : l'ordre est donc stable d'un rafraîchissement à l'autre.
    """
    from tierlists.models import ParticipantItemProgress

    item_ids = list(tier_list.items.values_list("id", flat=True))
    rows = []
    for participant in tier_list.participants.all():
        shuffled = list(item_ids)
        random.Random(participant.answer_order_seed).shuffle(shuffled)
        rows.extend(
            ParticipantItemProgress(
                participant=participant, item_id=item_id, display_order=position
            )
            for position, item_id in enumerate(shuffled)
        )
    ParticipantItemProgress.objects.bulk_create(rows, ignore_conflicts=True)


@transaction.atomic
def save_answer(participant, item, question, value: int):
    """Autosauvegarde d'une réponse (spec §20).

    Interdit dès que le participant a validé l'item : la règle est imposée par
    le backend, pas seulement par le frontend.
    """
    from tierlists.models import Answer, ParticipantItemProgress

    tier_list = participant.tier_list
    if tier_list.status != TierListStatus.ANSWERING:
        raise Conflict(
            "La Tier List n'est plus en phase de réponses.", code="not_answering"
        )

    progress = (
        ParticipantItemProgress.objects.select_for_update()
        .filter(participant=participant, item=item)
        .first()
    )
    if progress is None:
        raise BusinessError(
            "Cet item ne fait pas partie de ton questionnaire.", code="unknown_item"
        )
    if progress.is_validated:
        raise Conflict(
            "C'est verrouillé. Trop tard pour réécrire l'histoire.",
            code="item_already_validated",
        )

    if participant.answering_started_at is None:
        participant.answering_started_at = timezone.now()
        participant.save(update_fields=["answering_started_at"])

    answer, _created = Answer.objects.update_or_create(
        participant=participant, item=item, question=question, defaults={"value": value}
    )
    return answer


@transaction.atomic
def validate_item(participant, item):
    """Verrouille définitivement les six réponses d'un item (spec §20).

    Si c'est le dernier item du participant, il est marqué comme ayant terminé.
    Si c'est le dernier participant, le classement est calculé et la partie
    bascule en phase JOKER (spec §26).
    """
    from tierlists.models import Answer, ParticipantItemProgress, TierList

    tier_list = TierList.objects.select_for_update().get(pk=participant.tier_list_id)
    if tier_list.status != TierListStatus.ANSWERING:
        raise Conflict("La Tier List n'est plus en phase de réponses.", code="not_answering")

    progress = (
        ParticipantItemProgress.objects.select_for_update()
        .filter(participant=participant, item=item)
        .first()
    )
    if progress is None:
        raise BusinessError(
            "Cet item ne fait pas partie de ton questionnaire.", code="unknown_item"
        )
    if progress.is_validated:
        raise Conflict("Cet item est déjà validé.", code="item_already_validated")

    answered = Answer.objects.filter(participant=participant, item=item).count()
    if answered < REQUIRED_QUESTION_COUNT:
        raise BusinessError(
            f"Il manque des réponses : {answered}/{REQUIRED_QUESTION_COUNT}.",
            code="missing_answers",
        )

    progress.validate()

    remaining = ParticipantItemProgress.objects.filter(
        participant=participant, is_validated=False
    ).count()
    if remaining == 0 and participant.answering_completed_at is None:
        participant.answering_completed_at = timezone.now()
        participant.save(update_fields=["answering_completed_at"])
        logger.info(
            "Participant %s a terminé ses réponses (Tier List %s)",
            participant.user.username,
            tier_list.pk,
        )
        maybe_start_joker_phase(tier_list)

    return progress


def maybe_start_joker_phase(tier_list) -> bool:
    """Bascule en JOKER si tous les participants ont terminé. Renvoie True si bascule.

    L'appelant doit déjà détenir le verrou sur la Tier List.
    """
    from tierlists.models import JokerAction

    if tier_list.status != TierListStatus.ANSWERING:
        return False
    unfinished = tier_list.participants.filter(answering_completed_at__isnull=True).exists()
    if unfinished:
        return False

    build_ranking(tier_list)

    # Ordre des jokers : inverse de l'ordre de complétion (spec §34).
    # Départage déterministe en cas d'égalité de timestamp : id d'inscription.
    participants = sorted(
        tier_list.participants.all(),
        key=lambda p: (p.answering_completed_at, p.id),
        reverse=True,
    )
    joker_actions = []
    for position, participant in enumerate(participants, start=1):
        participant.joker_order = position
        participant.save(update_fields=["joker_order"])
        joker_actions.append(
            JokerAction(
                tier_list=tier_list, participant=participant, status=JokerStatus.PENDING
            )
        )
    JokerAction.objects.bulk_create(joker_actions, ignore_conflicts=True)

    tier_list.status = TierListStatus.JOKER
    tier_list.save(update_fields=["status", "updated_at"])
    logger.info("Tier List %s -> JOKER (%s jokers en attente)", tier_list.pk, len(participants))
    return True
