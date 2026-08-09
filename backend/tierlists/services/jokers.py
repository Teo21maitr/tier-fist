"""Phase joker (spec §33 à §40).

Chaque participant dispose d'exactement un joker. Les tours s'enchaînent dans
l'ordre inverse de complétion du questionnaire. Un item ne peut être déplacé
qu'une seule fois sur toute la partie.

Toutes les opérations verrouillent la Tier List : deux requêtes concurrentes ne
peuvent pas consommer le même tour ni déplacer le même item.
"""

from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from config.exceptions import BusinessError, Conflict
from tierlists.constants import RANK_NUMBERS, JokerStatus, TierListStatus

logger = logging.getLogger("tierfist")


def current_turn(tier_list):
    """Joker du participant dont c'est le tour, ou ``None`` si la phase est finie."""
    from tierlists.models import JokerAction

    return (
        JokerAction.objects.filter(tier_list=tier_list, status=JokerStatus.PENDING)
        .select_related("participant", "participant__user")
        .order_by("participant__joker_order", "participant_id")
        .first()
    )


def _load_turn(tier_list, user, *, require_creator: bool = False):
    """Vérifie l'état de la phase et renvoie ``(joker du tour, participant appelant)``."""
    from tierlists.models import JokerAction, TierListParticipant

    if tier_list.status != TierListStatus.JOKER:
        raise Conflict(
            "La phase joker n'est pas en cours.", code="not_joker_phase"
        )

    caller = TierListParticipant.objects.filter(tier_list=tier_list, user=user).first()
    if caller is None:
        raise BusinessError(
            "Tu ne fais pas partie de cette Tier List.", code="not_participant", status_code=403
        )

    turn = (
        JokerAction.objects.select_for_update()
        .filter(tier_list=tier_list, status=JokerStatus.PENDING)
        .select_related("participant")
        .order_by("participant__joker_order", "participant_id")
        .first()
    )
    if turn is None:
        raise Conflict("Tous les jokers ont déjà été joués.", code="jokers_done")

    if require_creator:
        if tier_list.creator_id != user.pk:
            raise BusinessError(
                "Seul le créateur peut forcer le passage d'un tour.",
                code="not_creator",
                status_code=403,
            )
    elif turn.participant_id != caller.pk:
        raise BusinessError(
            "Pas ton tour. La patience aussi mérite une note sur 9.",
            code="not_your_turn",
            status_code=403,
        )

    return turn, caller


@transaction.atomic
def use_joker(tier_list, user, item_id: int, to_rank: int):
    """Déplace un item vers un autre rang et consomme le joker du joueur actif."""
    from tierlists.models import Item, ItemScore, TierList

    tier_list = TierList.objects.select_for_update().get(pk=tier_list.pk)
    turn, _caller = _load_turn(tier_list, user)

    if to_rank not in RANK_NUMBERS:
        raise BusinessError("Ce rang n'existe pas.", code="invalid_rank")

    item = (
        Item.objects.select_for_update()
        .filter(pk=item_id, tier_list=tier_list)
        .first()
    )
    if item is None:
        raise BusinessError("Cet item n'appartient pas à cette Tier List.", code="unknown_item")
    if item.joker_locked:
        raise Conflict(
            "Cet item a déjà été déplacé par un joker. Une seule fois par partie.",
            code="item_joker_locked",
        )

    score = ItemScore.objects.select_for_update().filter(tier_list=tier_list, item=item).first()
    if score is None:
        raise BusinessError("Cet item n'a pas de classement.", code="missing_score")
    if score.current_rank == to_rank:
        raise BusinessError(
            "Cet item est déjà dans ce rang. Un joker, ça se mérite.",
            code="same_rank",
        )

    from_rank = score.current_rank
    score.current_rank = to_rank
    score.save(update_fields=["current_rank"])

    item.joker_locked = True
    item.save(update_fields=["joker_locked", "updated_at"])

    turn.item = item
    turn.from_rank = from_rank
    turn.to_rank = to_rank
    turn.status = JokerStatus.USED
    turn.played_at = timezone.now()
    turn.save(update_fields=["item", "from_rank", "to_rank", "status", "played_at"])

    logger.info(
        "Joker utilisé: Tier List %s, %s déplace %s de %s vers %s",
        tier_list.pk,
        user.username,
        item.name,
        from_rank,
        to_rank,
    )
    complete_if_finished(tier_list)
    return turn


@transaction.atomic
def skip_joker(tier_list, user):
    """Le joueur actif renonce explicitement à son joker (spec §38)."""
    from tierlists.models import TierList

    tier_list = TierList.objects.select_for_update().get(pk=tier_list.pk)
    turn, _caller = _load_turn(tier_list, user)

    turn.status = JokerStatus.SKIPPED
    turn.played_at = timezone.now()
    turn.save(update_fields=["status", "played_at"])
    logger.info("Joker abandonné: Tier List %s, %s", tier_list.pk, user.username)

    complete_if_finished(tier_list)
    return turn


@transaction.atomic
def force_skip_joker(tier_list, user):
    """Le créateur débloque la partie en faisant sauter le tour du joueur actif (spec §39)."""
    from tierlists.models import TierList

    tier_list = TierList.objects.select_for_update().get(pk=tier_list.pk)
    turn, _caller = _load_turn(tier_list, user, require_creator=True)

    turn.status = JokerStatus.FORCED_SKIP
    turn.played_at = timezone.now()
    turn.forced_by = user
    turn.save(update_fields=["status", "played_at", "forced_by"])
    logger.info(
        "Tour forcé: Tier List %s, %s a fait sauter le tour de %s",
        tier_list.pk,
        user.username,
        turn.participant.user.username,
    )

    complete_if_finished(tier_list)
    return turn


def complete_if_finished(tier_list) -> bool:
    """Passe en COMPLETED lorsque tous les jokers sont dans un état terminal (spec §40)."""
    from tierlists.models import ItemScore, JokerAction

    still_pending = JokerAction.objects.filter(
        tier_list=tier_list, status=JokerStatus.PENDING
    ).exists()
    if still_pending:
        return False

    # Le classement courant devient le classement définitif.
    for score in ItemScore.objects.filter(tier_list=tier_list):
        score.final_rank = score.current_rank
        score.save(update_fields=["final_rank"])

    tier_list.status = TierListStatus.COMPLETED
    tier_list.completed_at = timezone.now()
    tier_list.save(update_fields=["status", "completed_at", "updated_at"])
    logger.info("Tier List %s -> COMPLETED", tier_list.pk)
    return True
