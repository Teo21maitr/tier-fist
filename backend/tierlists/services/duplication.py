"""Duplication d'une Tier List (spec §42).

On recopie la structure (thème, rangs, questions + coefficients, items + images)
mais rien de ce qui appartient à la partie jouée : ni participants, ni réponses,
ni progression, ni scores, ni classement, ni jokers.
"""

from __future__ import annotations

import logging
from pathlib import Path

from django.core.files.base import ContentFile
from django.db import transaction

from tierlists.constants import RANK_FIELD_NAMES, TierListStatus

logger = logging.getLogger("tierfist")


@transaction.atomic
def duplicate_tier_list(source, user, name: str | None = None):
    from tierlists.models import Item, Question, TierList, TierListParticipant

    copy = TierList(
        name=(name or "").strip() or f"Copie de {source.name}",
        theme=source.theme,
        creator=user,
        status=TierListStatus.DRAFT,
    )
    for field in RANK_FIELD_NAMES:
        setattr(copy, field, getattr(source, field))
    copy.save()  # génère un nouveau code d'invitation

    # Le duplicateur devient créateur et premier participant.
    TierListParticipant.objects.create(tier_list=copy, user=user)

    Question.objects.bulk_create(
        [
            Question(
                tier_list=copy,
                text=question.text,
                coefficient=question.coefficient,
                display_order=question.display_order,
            )
            for question in source.questions.all().order_by("display_order", "id")
        ]
    )

    for item in source.items.all().order_by("id"):
        clone = Item(
            tier_list=copy,
            name=item.name,
            external_image_url=item.external_image_url,
        )
        if item.uploaded_image:
            # Copie physique du fichier : les deux Tier Lists restent
            # indépendantes, supprimer l'une n'ampute pas l'autre.
            try:
                item.uploaded_image.open("rb")
                content = item.uploaded_image.read()
                suffix = Path(item.uploaded_image.name).suffix or ".img"
                clone.uploaded_image.save(f"copy{suffix}", ContentFile(content), save=False)
            except (FileNotFoundError, OSError):
                logger.warning(
                    "Image introuvable lors de la duplication de l'item %s", item.pk
                )
            finally:
                item.uploaded_image.close()
        clone.save()

    logger.info("Tier List %s dupliquée en %s par %s", source.pk, copy.pk, user.username)
    return copy
