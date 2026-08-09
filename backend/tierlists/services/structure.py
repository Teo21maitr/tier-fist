"""Règles de structure d'une Tier List : questions, coefficients, finalisation."""

from __future__ import annotations

from collections import Counter

from tierlists.constants import (
    COEFFICIENT_SLOTS,
    REQUIRED_COEFFICIENT_DISTRIBUTION,
    REQUIRED_QUESTION_COUNT,
)


def used_coefficients(tier_list, exclude_question_id: int | None = None) -> Counter:
    queryset = tier_list.questions.all()
    if exclude_question_id is not None:
        queryset = queryset.exclude(pk=exclude_question_id)
    return Counter(queryset.values_list("coefficient", flat=True))


def available_coefficients(tier_list, exclude_question_id: int | None = None) -> list[int]:
    """Coefficients encore attribuables (spec §15.1).

    Exemple : si 1, 1, 2, 5 sont pris, seuls 2 et 3 restent proposables.
    """
    used = used_coefficients(tier_list, exclude_question_id)
    return [
        coefficient
        for coefficient, slots in sorted(COEFFICIENT_SLOTS.items())
        if used[coefficient] < slots
    ]


def coefficient_availability(tier_list, exclude_question_id: int | None = None) -> list[dict]:
    """Détail par coefficient, pour l'affichage du formulaire de question."""
    used = used_coefficients(tier_list, exclude_question_id)
    return [
        {
            "coefficient": coefficient,
            "slots": slots,
            "used": used[coefficient],
            "remaining": slots - used[coefficient],
        }
        for coefficient, slots in sorted(COEFFICIENT_SLOTS.items())
    ]


def finalization_blockers(tier_list) -> list[str]:
    """Liste des raisons empêchant la finalisation (spec §16). Vide = finalisable."""
    blockers: list[str] = []

    questions = list(tier_list.questions.values_list("coefficient", flat=True))
    if len(questions) != REQUIRED_QUESTION_COUNT:
        blockers.append(
            f"Il faut exactement {REQUIRED_QUESTION_COUNT} questions "
            f"(actuellement {len(questions)})."
        )
    if sorted(questions) != sorted(REQUIRED_COEFFICIENT_DISTRIBUTION):
        blockers.append(
            "Les coefficients doivent être exactement 1, 1, 2, 2, 3 et 5."
        )
    if not tier_list.items.exists():
        blockers.append("Il faut au moins un item à classer.")
    return blockers


def can_finalize(tier_list) -> bool:
    return not finalization_blockers(tier_list)
