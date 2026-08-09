"""Algorithme de classement automatique (spec §24 à §30).

Deux briques indépendantes :

1. :func:`assign_ranks` — fonction pure, sans base de données, qui répartit des
   items scorés dans les cinq rangs. C'est la spécification exécutable de
   l'algorithme (spec §62) : elle est testée directement avec des ``Decimal``.
2. :func:`build_ranking` — pipeline complet qui lit les réponses en base,
   calcule les scores collectifs et persiste les ``ItemScore``.

Précision : les scores collectifs sont des rationnels exacts de dénominateur
``14 × N``. Le classement compare donc les **numérateurs entiers**, ce qui rend
la détection des ex æquo exacte, indépendamment de tout arrondi. Le ``Decimal``
n'est utilisé que pour la restitution.
"""

from __future__ import annotations

import logging
from collections.abc import Hashable, Sequence
from decimal import Decimal
from typing import TypeVar

from django.db.models import F, Sum

from tierlists.constants import (
    COEFFICIENT_TOTAL,
    RANK_NUMBERS,
    S_RANK_TARGET_RATIO_PERCENT,
)

logger = logging.getLogger("tierfist")

K = TypeVar("K", bound=Hashable)

# Précision de stockage/restitution du score collectif.
SCORE_QUANTUM = Decimal("0.0000000001")


def compute_rank_sizes(total_items: int) -> list[int]:
    """Tailles cibles théoriques des rangs [S, A, B, C, D] (spec §27.2, §27.4).

    Les ex æquo peuvent ensuite faire dévier la répartition réelle : une égalité
    n'est jamais cassée pour satisfaire un quota.
    """
    if total_items <= 0:
        return [0, 0, 0, 0, 0]

    # ceil(total × 10 %) en arithmétique entière, sans flottant.
    s_target = -(-total_items * S_RANK_TARGET_RATIO_PERCENT // 100)
    s_target = min(max(1, s_target), total_items)

    remaining = total_items - s_target
    base, remainder = divmod(remaining, 4)
    # En cas de reste, les rangs les plus élevés sont favorisés.
    sizes = [
        s_target,
        base + (1 if remainder >= 1 else 0),
        base + (1 if remainder >= 2 else 0),
        base + (1 if remainder >= 3 else 0),
        base,
    ]
    return sizes


def assign_ranks(scored_items: Sequence[tuple[K, object]]) -> dict[K, int]:
    """Répartit des items scorés dans les rangs 1 à 5.

    :param scored_items: paires ``(clé, score)``. Le score doit être comparable
        et son égalité doit être exacte (``Decimal`` ou entier, jamais ``float``).
    :return: ``{clé: numéro de rang}``.

    Règles appliquées :
    - tri par score décroissant, clé croissante en cas d'ex æquo (affichage seul) ;
    - le rang 1 contient au moins un item ;
    - deux items de score strictement identique sont toujours dans le même rang :
      une frontière qui traverse un groupe d'ex æquo est repoussée, quitte à
      surcharger le rang supérieur et à vider le suivant.
    """
    ordered = sorted(scored_items, key=lambda pair: (_negate(pair[1]), pair[0]))
    total = len(ordered)
    if total == 0:
        return {}

    sizes = compute_rank_sizes(total)

    # Positions de coupe cumulées, puis repoussées hors des groupes d'ex æquo.
    cuts: list[int] = []
    cursor = 0
    previous_cut = 0
    for size in sizes[:-1]:
        cursor += size
        cut = min(max(cursor, previous_cut), total)
        while 0 < cut < total and ordered[cut][1] == ordered[cut - 1][1]:
            cut += 1
        cuts.append(cut)
        previous_cut = cut

    boundaries = [0, *cuts, total]
    assignment: dict[K, int] = {}
    for rank_index, rank_number in enumerate(RANK_NUMBERS):
        start, end = boundaries[rank_index], boundaries[rank_index + 1]
        for key, _score in ordered[start:end]:
            assignment[key] = rank_number
    return assignment


def _negate(value):
    """Inverse un score pour un tri décroissant, en préservant l'exactitude."""
    return -value


def rank_groups(scored_items: Sequence[tuple[K, object]]) -> dict[int, list[K]]:
    """Version « groupée » de :func:`assign_ranks`, ordonnée à l'intérieur d'un rang."""
    assignment = assign_ranks(scored_items)
    ordered = sorted(scored_items, key=lambda pair: (_negate(pair[1]), pair[0]))
    groups: dict[int, list[K]] = {number: [] for number in RANK_NUMBERS}
    for key, _score in ordered:
        groups[assignment[key]].append(key)
    return groups


# ---------------------------------------------------------------------------
# Pipeline base de données
# ---------------------------------------------------------------------------


def compute_weighted_totals(tier_list) -> dict[int, int]:
    """Somme ``Σ(réponse × coefficient)`` par item, tous participants confondus.

    Entier exact : c'est le numérateur du score collectif.
    """
    from tierlists.models import Answer, Item

    rows = (
        Answer.objects.filter(participant__tier_list=tier_list)
        .values("item_id")
        .annotate(weighted=Sum(F("value") * F("question__coefficient")))
    )
    totals = {row["item_id"]: int(row["weighted"]) for row in rows}
    # Un item sans aucune réponse ne doit pas disparaître du classement.
    for item_id in Item.objects.filter(tier_list=tier_list).values_list("id", flat=True):
        totals.setdefault(item_id, 0)
    return totals


def global_score_decimal(weighted_total: int, participant_count: int) -> Decimal:
    """``Σ(réponse × coef) / (14 × N)`` — le score collectif, entre 1 et 9."""
    if participant_count <= 0:
        return Decimal("0")
    denominator = Decimal(COEFFICIENT_TOTAL * participant_count)
    return (Decimal(weighted_total) / denominator).quantize(SCORE_QUANTUM)


def build_ranking(tier_list) -> list:
    """Calcule et persiste le classement initial d'une Tier List.

    Appelé une seule fois, lorsque le dernier participant termine ses réponses
    (spec §26). Doit être exécuté dans une transaction par l'appelant.
    """
    from tierlists.models import ItemScore

    participant_count = tier_list.participants.count()
    totals = compute_weighted_totals(tier_list)
    assignment = assign_ranks(list(totals.items()))

    ItemScore.objects.filter(tier_list=tier_list).delete()
    scores = [
        ItemScore(
            tier_list=tier_list,
            item_id=item_id,
            global_score=global_score_decimal(weighted, participant_count),
            algorithm_rank=assignment[item_id],
            current_rank=assignment[item_id],
        )
        for item_id, weighted in totals.items()
    ]
    ItemScore.objects.bulk_create(scores)
    logger.info(
        "Classement calculé pour la Tier List %s (%s items, %s participants)",
        tier_list.pk,
        len(scores),
        participant_count,
    )
    return scores
