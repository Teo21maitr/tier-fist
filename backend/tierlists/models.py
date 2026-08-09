"""Modèle de données Tier Fist (spec §48).

Note d'implémentation : la spec évoque un champ ``joker_status`` sur
``TierListParticipant`` *et* un statut sur ``JokerAction``. Dupliquer cet état
serait une source de divergence ; l'état du joker vit donc uniquement sur
``JokerAction`` (une par participant, créée à l'entrée en phase JOKER).
Voir docs/DECISIONS.md.
"""

from __future__ import annotations

import secrets

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from common.uploads import item_image_upload_to
from tierlists.constants import (
    ALLOWED_COEFFICIENTS,
    DEFAULT_RANK_NAMES,
    INVITE_CODE_ALPHABET,
    INVITE_CODE_LENGTH,
    MAX_ANSWER_VALUE,
    MIN_ANSWER_VALUE,
    RANK_NUMBERS,
    JokerStatus,
    TierListStatus,
)


def generate_invite_code() -> str:
    return "".join(secrets.choice(INVITE_CODE_ALPHABET) for _ in range(INVITE_CODE_LENGTH))


class TierList(models.Model):
    name = models.CharField("nom", max_length=120)
    theme = models.CharField("thème", max_length=120)
    invite_code = models.CharField(
        "code d'invitation", max_length=INVITE_CODE_LENGTH, unique=True, db_index=True
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_tier_lists",
        verbose_name="créateur",
    )
    status = models.CharField(
        "statut",
        max_length=12,
        choices=TierListStatus.choices,
        default=TierListStatus.DRAFT,
        db_index=True,
    )
    rank_1_name = models.CharField("rang 1", max_length=30, default=DEFAULT_RANK_NAMES[0])
    rank_2_name = models.CharField("rang 2", max_length=30, default=DEFAULT_RANK_NAMES[1])
    rank_3_name = models.CharField("rang 3", max_length=30, default=DEFAULT_RANK_NAMES[2])
    rank_4_name = models.CharField("rang 4", max_length=30, default=DEFAULT_RANK_NAMES[3])
    rank_5_name = models.CharField("rang 5", max_length=30, default=DEFAULT_RANK_NAMES[4])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Tier List"
        verbose_name_plural = "Tier Lists"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.invite_code})"

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = self._generate_unique_invite_code()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_unique_invite_code() -> str:
        for _ in range(50):
            code = generate_invite_code()
            if not TierList.objects.filter(invite_code=code).exists():
                return code
        raise RuntimeError("Impossible de générer un code d'invitation unique.")

    # --- Rangs -------------------------------------------------------------
    @property
    def rank_names(self) -> list[str]:
        return [getattr(self, f"rank_{number}_name") for number in RANK_NUMBERS]

    def rank_name(self, number: int) -> str:
        return getattr(self, f"rank_{number}_name")

    # --- Aides d'état ------------------------------------------------------
    @property
    def is_draft(self) -> bool:
        return self.status == TierListStatus.DRAFT

    @property
    def structure_is_frozen(self) -> bool:
        """Après finalisation, items/questions/rangs/participants sont figés."""
        return self.status != TierListStatus.DRAFT

    @property
    def results_are_visible(self) -> bool:
        return self.status in (TierListStatus.JOKER, TierListStatus.COMPLETED)


class TierListParticipant(models.Model):
    tier_list = models.ForeignKey(
        TierList, on_delete=models.CASCADE, related_name="participants"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="participations"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    answering_started_at = models.DateTimeField(null=True, blank=True)
    answering_completed_at = models.DateTimeField(null=True, blank=True)
    # Seed persistante : garantit un ordre d'items stable pour ce participant
    # (spec §17 : pas de reshuffle à chaque refresh).
    answer_order_seed = models.BigIntegerField(default=0)
    # Position dans la file des jokers (1 = joue en premier), calculée à
    # l'entrée en phase JOKER.
    joker_order = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "participant"
        constraints = [
            models.UniqueConstraint(
                fields=["tier_list", "user"], name="unique_participant_per_tier_list"
            )
        ]
        ordering = ["joined_at", "id"]

    def __str__(self) -> str:
        return f"{self.user} @ {self.tier_list.name}"

    def save(self, *args, **kwargs):
        if not self.answer_order_seed:
            self.answer_order_seed = secrets.randbits(62)
        super().save(*args, **kwargs)

    @property
    def has_finished_answering(self) -> bool:
        return self.answering_completed_at is not None


class Item(models.Model):
    tier_list = models.ForeignKey(TierList, on_delete=models.CASCADE, related_name="items")
    name = models.CharField("nom", max_length=120)
    # Nom normalisé (trim + minuscules) servant l'unicité insensible à la casse.
    normalized_name = models.CharField(max_length=120, editable=False)
    uploaded_image = models.ImageField(
        "image uploadée", upload_to=item_image_upload_to, blank=True, null=True
    )
    external_image_url = models.URLField("image distante", max_length=500, blank=True)
    # Un item ne peut être déplacé que par un seul joker sur toute la partie.
    joker_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "item"
        constraints = [
            models.UniqueConstraint(
                fields=["tier_list", "normalized_name"], name="unique_item_name_per_tier_list"
            )
        ]
        ordering = ["id"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        self.normalized_name = self.normalize(self.name)
        if "update_fields" in kwargs and kwargs["update_fields"] is not None:
            update_fields = set(kwargs["update_fields"])
            if "name" in update_fields:
                update_fields.add("normalized_name")
            kwargs["update_fields"] = list(update_fields)
        super().save(*args, **kwargs)

    @staticmethod
    def normalize(name: str) -> str:
        return " ".join(name.strip().split()).casefold()

    @property
    def image_url(self) -> str | None:
        """Priorité explicite : l'upload local prime sur l'URL distante (spec §48.4)."""
        if self.uploaded_image:
            return self.uploaded_image.url
        return self.external_image_url or None


class Question(models.Model):
    tier_list = models.ForeignKey(TierList, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField("affirmation", max_length=300)
    coefficient = models.PositiveSmallIntegerField("coefficient")
    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "question"
        constraints = [
            models.CheckConstraint(
                check=Q(coefficient__in=ALLOWED_COEFFICIENTS),
                name="question_coefficient_allowed",
            )
        ]
        ordering = ["display_order", "id"]

    def __str__(self) -> str:
        return f"[{self.coefficient}] {self.text[:40]}"


class Answer(models.Model):
    participant = models.ForeignKey(
        TierListParticipant, on_delete=models.CASCADE, related_name="answers"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    value = models.PositiveSmallIntegerField("valeur")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "réponse"
        constraints = [
            models.UniqueConstraint(
                fields=["participant", "item", "question"], name="unique_answer_per_cell"
            ),
            models.CheckConstraint(
                check=Q(value__gte=MIN_ANSWER_VALUE) & Q(value__lte=MAX_ANSWER_VALUE),
                name="answer_value_between_1_and_9",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.participant_id}/{self.item_id}/{self.question_id} = {self.value}"


class ParticipantItemProgress(models.Model):
    """Ordre d'affichage et verrouillage d'un item pour un participant (spec §48.7)."""

    participant = models.ForeignKey(
        TierListParticipant, on_delete=models.CASCADE, related_name="item_progress"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="participant_progress")
    display_order = models.PositiveIntegerField()
    is_validated = models.BooleanField(default=False)
    validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "progression item"
        verbose_name_plural = "progressions item"
        constraints = [
            models.UniqueConstraint(
                fields=["participant", "item"], name="unique_progress_per_participant_item"
            )
        ]
        ordering = ["display_order", "id"]

    def __str__(self) -> str:
        return f"{self.participant_id}/{self.item_id}"

    def validate(self) -> None:
        self.is_validated = True
        self.validated_at = timezone.now()
        self.save(update_fields=["is_validated", "validated_at"])


class ItemScore(models.Model):
    """Score collectif et rangs d'un item (spec §48.8)."""

    tier_list = models.ForeignKey(TierList, on_delete=models.CASCADE, related_name="scores")
    item = models.OneToOneField(Item, on_delete=models.CASCADE, related_name="score")
    # Précision volontairement large : le classement compare des égalités exactes.
    global_score = models.DecimalField(max_digits=16, decimal_places=10)
    # Rang issu de l'algorithme : ne change jamais.
    algorithm_rank = models.PositiveSmallIntegerField()
    # Rang courant : évolue avec les jokers.
    current_rank = models.PositiveSmallIntegerField()
    # Rang définitif : figé au passage en COMPLETED.
    final_rank = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "score d'item"
        verbose_name_plural = "scores d'items"
        ordering = ["-global_score", "item_id"]

    def __str__(self) -> str:
        return f"{self.item.name}: {self.global_score}"


class JokerAction(models.Model):
    """Joker d'un participant : un seul par participant et par partie (spec §48.9)."""

    tier_list = models.ForeignKey(
        TierList, on_delete=models.CASCADE, related_name="joker_actions"
    )
    participant = models.OneToOneField(
        TierListParticipant, on_delete=models.CASCADE, related_name="joker"
    )
    item = models.ForeignKey(
        Item, on_delete=models.SET_NULL, null=True, blank=True, related_name="joker_actions"
    )
    from_rank = models.PositiveSmallIntegerField(null=True, blank=True)
    to_rank = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=12, choices=JokerStatus.choices, default=JokerStatus.PENDING
    )
    played_at = models.DateTimeField(null=True, blank=True)
    forced_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="forced_jokers",
    )

    class Meta:
        verbose_name = "joker"
        ordering = ["participant__joker_order", "id"]

    def __str__(self) -> str:
        return f"Joker {self.participant_id} ({self.status})"

    @property
    def is_terminal(self) -> bool:
        return self.status != JokerStatus.PENDING
