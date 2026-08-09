from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from accounts.serializers import PublicUserSerializer
from common.uploads import normalize_uploaded_image_name, validate_image_upload
from tierlists.constants import (
    ALLOWED_COEFFICIENTS,
    COEFFICIENT_SLOTS,
    MAX_ANSWER_VALUE,
    MIN_ANSWER_VALUE,
    RANK_COLORS,
    RANK_FIELD_NAMES,
    RANK_NUMBERS,
    JokerStatus,
)
from tierlists.models import Item, Question, TierList, TierListParticipant
from tierlists.services.structure import (
    coefficient_availability,
    finalization_blockers,
    used_coefficients,
)

DISPLAY_QUANTUM = Decimal("0.01")


def _absolute(request, url: str | None) -> str | None:
    if not url:
        return None
    if request is None or url.startswith(("http://", "https://")):
        return url
    return request.build_absolute_uri(url)


def rank_payload(tier_list: TierList) -> list[dict]:
    return [
        {"number": number, "name": tier_list.rank_name(number), "color": RANK_COLORS[index]}
        for index, number in enumerate(RANK_NUMBERS)
    ]


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


class ItemSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    has_image = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = ["id", "name", "image_url", "has_image", "joker_locked"]
        read_only_fields = fields

    def get_image_url(self, obj: Item) -> str | None:
        return _absolute(self.context.get("request"), obj.image_url)

    def get_has_image(self, obj: Item) -> bool:
        return bool(obj.image_url)


class ItemWriteSerializer(serializers.ModelSerializer):
    remove_image = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = Item
        fields = ["name", "uploaded_image", "external_image_url", "remove_image"]
        extra_kwargs = {
            "uploaded_image": {"required": False, "allow_null": True},
            "external_image_url": {"required": False, "allow_blank": True},
        }

    def validate_name(self, value: str) -> str:
        value = " ".join(value.strip().split())
        if not value:
            raise serializers.ValidationError("Le nom de l'item est obligatoire.")

        tier_list = self.context["tier_list"]
        queryset = Item.objects.filter(
            tier_list=tier_list, normalized_name=Item.normalize(value)
        )
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                "Cet item existe déjà. Même Laurent refuse de le noter deux fois."
            )
        return value

    def validate_uploaded_image(self, value):
        if value in (None, ""):
            return value
        try:
            extension = validate_image_upload(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        normalize_uploaded_image_name(value, extension)
        return value

    def validate_external_image_url(self, value: str) -> str:
        value = (value or "").strip()
        if value and not value.startswith(("http://", "https://")):
            raise serializers.ValidationError("L'URL doit commencer par http:// ou https://.")
        return value

    def _apply_image_rules(self, validated_data, instance: Item | None) -> None:
        """Un item n'a jamais besoin des deux sources d'image en même temps.

        L'upload local prime : fournir un fichier efface l'URL distante.
        """
        if validated_data.pop("remove_image", False):
            if instance is not None and instance.uploaded_image:
                instance.uploaded_image.delete(save=False)
            validated_data["uploaded_image"] = None
            validated_data["external_image_url"] = ""
            return

        if validated_data.get("uploaded_image"):
            if instance is not None and instance.uploaded_image:
                instance.uploaded_image.delete(save=False)
            validated_data["external_image_url"] = ""
        elif validated_data.get("external_image_url"):
            if instance is not None and instance.uploaded_image:
                instance.uploaded_image.delete(save=False)
            validated_data["uploaded_image"] = None

    def create(self, validated_data):
        self._apply_image_rules(validated_data, None)
        return Item.objects.create(tier_list=self.context["tier_list"], **validated_data)

    def update(self, instance: Item, validated_data):
        self._apply_image_rules(validated_data, instance)
        return super().update(instance, validated_data)


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------


class QuestionSerializer(serializers.ModelSerializer):
    """Question avec son coefficient : visible uniquement pendant DRAFT (spec §15.3)."""

    class Meta:
        model = Question
        fields = ["id", "text", "coefficient", "display_order"]
        read_only_fields = fields


class QuestionForAnsweringSerializer(serializers.ModelSerializer):
    """Question sans coefficient : pendant le questionnaire, il reste caché."""

    class Meta:
        model = Question
        fields = ["id", "text", "display_order"]
        read_only_fields = fields


class QuestionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ["text", "coefficient"]

    def validate_text(self, value: str) -> str:
        value = value.strip()
        if len(value) < 5:
            raise serializers.ValidationError(
                "L'affirmation est un peu courte. Laurent aime les phrases entières."
            )
        return value

    def validate_coefficient(self, value: int) -> int:
        if value not in ALLOWED_COEFFICIENTS:
            raise serializers.ValidationError("Coefficient invalide : choisis 1, 2, 3 ou 5.")
        return value

    def validate(self, attrs):
        tier_list = self.context["tier_list"]
        coefficient = attrs.get("coefficient")
        if coefficient is None:
            return attrs

        exclude_id = self.instance.pk if self.instance is not None else None
        used = used_coefficients(tier_list, exclude_question_id=exclude_id)
        if used[coefficient] >= COEFFICIENT_SLOTS[coefficient]:
            message = "Ce coefficient est déjà entièrement utilisé."
            if coefficient == 5:
                message = "Le coefficient 5 est déjà occupé. Il n'y a qu'un patron ici."
            raise serializers.ValidationError({"coefficient": message})
        return attrs


# ---------------------------------------------------------------------------
# Participants
# ---------------------------------------------------------------------------


class ParticipantSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(read_only=True)
    is_creator = serializers.SerializerMethodField()

    class Meta:
        model = TierListParticipant
        fields = ["id", "user", "is_creator", "joined_at"]
        read_only_fields = fields

    def get_is_creator(self, obj: TierListParticipant) -> bool:
        return obj.user_id == obj.tier_list.creator_id


class ParticipantProgressSerializer(serializers.Serializer):
    """Avancement d'un participant : pourcentage et statut, jamais les réponses (spec §22)."""

    id = serializers.IntegerField()
    user = PublicUserSerializer()
    is_creator = serializers.BooleanField()
    validated_items = serializers.IntegerField()
    total_items = serializers.IntegerField()
    progress_percent = serializers.IntegerField()
    has_finished = serializers.BooleanField()


# ---------------------------------------------------------------------------
# Tier List
# ---------------------------------------------------------------------------


class TierListCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TierList
        fields = ["name", "theme"]

    def validate_name(self, value: str) -> str:
        value = " ".join(value.strip().split())
        if not value:
            raise serializers.ValidationError("Donne un nom à ta Tier List.")
        return value

    def validate_theme(self, value: str) -> str:
        value = " ".join(value.strip().split())
        if not value:
            raise serializers.ValidationError(
                "Donne-moi un sujet. J'essaierai de ne juger personne."
            )
        return value


class TierListUpdateSerializer(serializers.ModelSerializer):
    """Édition pendant DRAFT : nom, thème et les cinq noms de rang (spec §13)."""

    class Meta:
        model = TierList
        fields = ["name", "theme", *RANK_FIELD_NAMES]

    def validate(self, attrs):
        for field in RANK_FIELD_NAMES:
            if field in attrs:
                value = " ".join(str(attrs[field]).strip().split())
                if not value:
                    raise serializers.ValidationError(
                        {field: "Un rang ne peut pas avoir un nom vide."}
                    )
                attrs[field] = value
        for field in ("name", "theme"):
            if field in attrs:
                value = " ".join(str(attrs[field]).strip().split())
                if not value:
                    raise serializers.ValidationError({field: "Ce champ est obligatoire."})
                attrs[field] = value
        return attrs


class TierListSerializer(serializers.ModelSerializer):
    creator = PublicUserSerializer(read_only=True)
    ranks = serializers.SerializerMethodField()
    participants_count = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    questions_count = serializers.SerializerMethodField()
    is_creator = serializers.SerializerMethodField()
    can_finalize = serializers.SerializerMethodField()
    finalization_blockers = serializers.SerializerMethodField()
    coefficients = serializers.SerializerMethodField()
    viewer = serializers.SerializerMethodField()

    class Meta:
        model = TierList
        fields = [
            "id",
            "name",
            "theme",
            "invite_code",
            "status",
            "creator",
            "ranks",
            "participants_count",
            "items_count",
            "questions_count",
            "is_creator",
            "can_finalize",
            "finalization_blockers",
            "coefficients",
            "viewer",
            "created_at",
            "updated_at",
            "finalized_at",
            "completed_at",
        ]
        read_only_fields = fields

    def get_ranks(self, obj: TierList) -> list[dict]:
        return rank_payload(obj)

    def get_participants_count(self, obj: TierList) -> int:
        return obj.participants.count()

    def get_items_count(self, obj: TierList) -> int:
        return obj.items.count()

    def get_questions_count(self, obj: TierList) -> int:
        return obj.questions.count()

    def get_is_creator(self, obj: TierList) -> bool:
        request = self.context.get("request")
        return bool(request and obj.creator_id == request.user.pk)

    def get_can_finalize(self, obj: TierList) -> bool:
        if not obj.is_draft or not self.get_is_creator(obj):
            return False
        return not finalization_blockers(obj)

    def get_finalization_blockers(self, obj: TierList) -> list[str]:
        return finalization_blockers(obj) if obj.is_draft else []

    def get_coefficients(self, obj: TierList) -> list[dict]:
        return coefficient_availability(obj) if obj.is_draft else []

    def get_viewer(self, obj: TierList) -> dict:
        """Ce que l'utilisateur courant doit faire : pilote l'accueil (spec §43)."""
        from tierlists.services.jokers import current_turn
        from tierlists.services.progress import participant_progress

        request = self.context.get("request")
        if request is None:
            return {}
        participant = obj.participants.filter(user=request.user).first()
        if participant is None:
            return {}

        progress = participant_progress(participant)
        joker = getattr(participant, "joker", None)
        turn = current_turn(obj) if obj.status == "JOKER" else None
        return {
            "participant_id": participant.pk,
            "validated_items": progress["validated_items"],
            "total_items": progress["total_items"],
            "progress_percent": progress["progress_percent"],
            "has_finished_answering": participant.has_finished_answering,
            "joker_status": joker.status if joker else None,
            "is_my_joker_turn": bool(turn and turn.participant_id == participant.pk),
            "waiting_for_others": (
                obj.status == "ANSWERING" and participant.has_finished_answering
            ),
        }


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


class JoinSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=16)

    def validate_code(self, value: str) -> str:
        return value.strip().upper().replace(" ", "")


OUT_OF_SCALE_MESSAGE = (
    "Choisis une valeur entre 1 et 9. Même pour Laurent, 12 est un peu excessif."
)


class AnswerWriteSerializer(serializers.Serializer):
    value = serializers.IntegerField(
        min_value=MIN_ANSWER_VALUE,
        max_value=MAX_ANSWER_VALUE,
        error_messages={
            "min_value": OUT_OF_SCALE_MESSAGE,
            "max_value": OUT_OF_SCALE_MESSAGE,
            "invalid": "Choisis une valeur entière entre 1 et 9.",
        },
    )


class JokerUseSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    to_rank = serializers.IntegerField(min_value=1, max_value=5)


class DuplicateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False, allow_blank=True)


class JokerActionSerializer(serializers.Serializer):
    participant_id = serializers.IntegerField()
    user = PublicUserSerializer()
    joker_order = serializers.IntegerField(allow_null=True)
    status = serializers.CharField()
    status_label = serializers.CharField()
    item = ItemSerializer(allow_null=True)
    from_rank = serializers.IntegerField(allow_null=True)
    to_rank = serializers.IntegerField(allow_null=True)
    played_at = serializers.DateTimeField(allow_null=True)
    forced_by = PublicUserSerializer(allow_null=True)


def serialize_joker_action(action, request=None) -> dict:
    return {
        "participant_id": action.participant_id,
        "user": PublicUserSerializer(action.participant.user, context={"request": request}).data,
        "joker_order": action.participant.joker_order,
        "status": action.status,
        "status_label": JokerStatus(action.status).label,
        "item": ItemSerializer(action.item, context={"request": request}).data
        if action.item
        else None,
        "from_rank": action.from_rank,
        "to_rank": action.to_rank,
        "played_at": action.played_at,
        "forced_by": PublicUserSerializer(action.forced_by, context={"request": request}).data
        if action.forced_by
        else None,
    }
