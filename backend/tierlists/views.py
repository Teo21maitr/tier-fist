from __future__ import annotations

import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from config.exceptions import BusinessError
from tierlists.constants import REQUIRED_QUESTION_COUNT, TierListStatus
from tierlists.models import (
    Answer,
    Item,
    ParticipantItemProgress,
    Question,
    TierList,
    TierListParticipant,
)
from tierlists.permissions import (
    get_participant,
    get_participant_tier_list,
    require_creator,
    require_draft,
    require_status,
)
from tierlists.serializers import (
    AnswerWriteSerializer,
    DuplicateSerializer,
    ItemSerializer,
    ItemWriteSerializer,
    JoinSerializer,
    JokerUseSerializer,
    ParticipantSerializer,
    QuestionForAnsweringSerializer,
    QuestionSerializer,
    QuestionWriteSerializer,
    TierListCreateSerializer,
    TierListSerializer,
    TierListUpdateSerializer,
    serialize_joker_action,
)
from tierlists.services import jokers as joker_service
from tierlists.services.duplication import duplicate_tier_list
from tierlists.services.lifecycle import finalize_tier_list, save_answer, validate_item
from tierlists.services.progress import all_participants_progress, participant_progress
from tierlists.services.results import item_result_detail, ranking_payload

logger = logging.getLogger("tierfist")


class TierListBaseView(APIView):
    """Résout la Tier List en la filtrant systématiquement par participation."""

    def get_tier_list(self, request, pk) -> TierList:
        return get_participant_tier_list(request.user, pk)

    def serialize(self, tier_list, request) -> dict:
        return TierListSerializer(tier_list, context={"request": request}).data


# ---------------------------------------------------------------------------
# Tier Lists
# ---------------------------------------------------------------------------


class TierListCollectionView(APIView):
    def get(self, request):
        """Les Tier Lists auxquelles l'utilisateur participe (spec §44)."""
        queryset = (
            TierList.objects.filter(participants__user=request.user)
            .select_related("creator")
            .prefetch_related("participants__user")
            .distinct()
            .order_by("-updated_at")
        )
        status_filter = request.query_params.get("status")
        if status_filter == "ongoing":
            queryset = queryset.exclude(status=TierListStatus.COMPLETED)
        elif status_filter == "completed":
            queryset = queryset.filter(status=TierListStatus.COMPLETED)
        elif status_filter in TierListStatus.values:
            queryset = queryset.filter(status=status_filter)

        serializer = TierListSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)

    @transaction.atomic
    def post(self, request):
        serializer = TierListCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tier_list = TierList.objects.create(creator=request.user, **serializer.validated_data)
        # Le créateur est automatiquement participant (spec §9).
        TierListParticipant.objects.create(tier_list=tier_list, user=request.user)
        logger.info(
            "Tier List créée: %s (code %s) par %s",
            tier_list.pk,
            tier_list.invite_code,
            request.user.username,
        )
        return Response(
            TierListSerializer(tier_list, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class TierListDetailView(TierListBaseView):
    def get(self, request, pk):
        tier_list = self.get_tier_list(request, pk)
        return Response(self.serialize(tier_list, request))

    def patch(self, request, pk):
        tier_list = self.get_tier_list(request, pk)
        # Tous les participants peuvent renommer les rangs pendant DRAFT (spec §12).
        require_draft(tier_list)
        serializer = TierListUpdateSerializer(tier_list, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self.serialize(tier_list, request))

    def delete(self, request, pk):
        tier_list = self.get_tier_list(request, pk)
        require_creator(tier_list, request.user, "supprimer la Tier List")
        logger.info("Tier List %s supprimée par %s", tier_list.pk, request.user.username)
        _delete_media(tier_list)
        tier_list.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _delete_media(tier_list) -> None:
    """Supprime les fichiers locaux associés (spec §41)."""
    for item in tier_list.items.exclude(uploaded_image=""):
        if item.uploaded_image:
            item.uploaded_image.delete(save=False)


class TierListJoinView(APIView):
    @transaction.atomic
    def post(self, request):
        serializer = JoinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]

        tier_list = TierList.objects.select_for_update().filter(invite_code=code).first()
        if tier_list is None:
            raise BusinessError(
                "Ce code ne correspond à aucune Tier List. Laurent a vérifié deux fois.",
                code="unknown_code",
                status_code=404,
            )

        existing = TierListParticipant.objects.filter(
            tier_list=tier_list, user=request.user
        ).first()
        if existing is not None:
            # Déjà membre : pas de doublon, on redirige simplement.
            return Response(
                {
                    "already_member": True,
                    "tier_list": TierListSerializer(
                        tier_list, context={"request": request}
                    ).data,
                }
            )

        if tier_list.status != TierListStatus.DRAFT:
            raise BusinessError(
                "Trop tard, cette Tier List est déjà lancée.",
                code="already_finalized",
                status_code=409,
            )

        TierListParticipant.objects.create(tier_list=tier_list, user=request.user)
        logger.info("%s a rejoint la Tier List %s", request.user.username, tier_list.pk)
        return Response(
            {
                "already_member": False,
                "tier_list": TierListSerializer(tier_list, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class TierListFinalizeView(TierListBaseView):
    def post(self, request, pk):
        tier_list = self.get_tier_list(request, pk)
        tier_list = finalize_tier_list(tier_list, request.user)
        return Response(self.serialize(tier_list, request))


class TierListDuplicateView(TierListBaseView):
    def post(self, request, pk):
        tier_list = self.get_tier_list(request, pk)
        serializer = DuplicateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        copy = duplicate_tier_list(
            tier_list, request.user, serializer.validated_data.get("name")
        )
        return Response(
            TierListSerializer(copy, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class TierListParticipantsView(TierListBaseView):
    def get(self, request, pk):
        tier_list = self.get_tier_list(request, pk)
        if tier_list.status == TierListStatus.DRAFT:
            participants = tier_list.participants.select_related("user", "tier_list")
            return Response(
                ParticipantSerializer(
                    participants, many=True, context={"request": request}
                ).data
            )
        # Dès ANSWERING, on expose aussi l'avancement (jamais les réponses).
        return Response(all_participants_progress(tier_list, request))


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


class ItemCollectionView(TierListBaseView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request, pk):
        tier_list = self.get_tier_list(request, pk)
        items = tier_list.items.all()
        return Response(ItemSerializer(items, many=True, context={"request": request}).data)

    def post(self, request, pk):
        tier_list = self.get_tier_list(request, pk)
        require_draft(tier_list)
        serializer = ItemWriteSerializer(
            data=request.data, context={"request": request, "tier_list": tier_list}
        )
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        return Response(
            ItemSerializer(item, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ItemDetailView(TierListBaseView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def patch(self, request, pk, item_id):
        tier_list = self.get_tier_list(request, pk)
        require_draft(tier_list)
        item = get_object_or_404(Item, pk=item_id, tier_list=tier_list)
        serializer = ItemWriteSerializer(
            item,
            data=request.data,
            partial=True,
            context={"request": request, "tier_list": tier_list},
        )
        serializer.is_valid(raise_exception=True)
        item = serializer.save()
        return Response(ItemSerializer(item, context={"request": request}).data)

    def delete(self, request, pk, item_id):
        tier_list = self.get_tier_list(request, pk)
        require_draft(tier_list)
        item = get_object_or_404(Item, pk=item_id, tier_list=tier_list)
        if item.uploaded_image:
            item.uploaded_image.delete(save=False)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------


class QuestionCollectionView(TierListBaseView):
    def get(self, request, pk):
        tier_list = self.get_tier_list(request, pk)
        questions = tier_list.questions.all()
        # Le coefficient n'est visible que pendant DRAFT (spec §15.3).
        serializer_class = (
            QuestionSerializer if tier_list.is_draft else QuestionForAnsweringSerializer
        )
        if tier_list.results_are_visible:
            # Une fois les résultats connus, le coefficient n'est plus un secret.
            serializer_class = QuestionSerializer
        return Response(serializer_class(questions, many=True).data)

    def post(self, request, pk):
        tier_list = self.get_tier_list(request, pk)
        require_draft(tier_list)
        # Verrou : deux participants ne peuvent pas prendre le même emplacement
        # de coefficient simultanément (spec §52).
        with transaction.atomic():
            locked = TierList.objects.select_for_update().get(pk=tier_list.pk)
            if locked.questions.count() >= REQUIRED_QUESTION_COUNT:
                raise BusinessError(
                    "Six questions. Pas cinq, pas sept. Je sais compter, profitez-en.",
                    code="too_many_questions",
                    status_code=409,
                )
            serializer = QuestionWriteSerializer(
                data=request.data, context={"request": request, "tier_list": locked}
            )
            serializer.is_valid(raise_exception=True)
            next_order = (locked.questions.count() or 0) + 1
            question = serializer.save(tier_list=locked, display_order=next_order)
        return Response(QuestionSerializer(question).data, status=status.HTTP_201_CREATED)


class QuestionDetailView(TierListBaseView):
    def patch(self, request, pk, question_id):
        tier_list = self.get_tier_list(request, pk)
        require_draft(tier_list)
        with transaction.atomic():
            locked = TierList.objects.select_for_update().get(pk=tier_list.pk)
            question = get_object_or_404(Question, pk=question_id, tier_list=locked)
            serializer = QuestionWriteSerializer(
                question,
                data=request.data,
                partial=True,
                context={"request": request, "tier_list": locked},
            )
            serializer.is_valid(raise_exception=True)
            question = serializer.save()
        return Response(QuestionSerializer(question).data)

    def delete(self, request, pk, question_id):
        tier_list = self.get_tier_list(request, pk)
        require_draft(tier_list)
        question = get_object_or_404(Question, pk=question_id, tier_list=tier_list)
        question.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Questionnaire
# ---------------------------------------------------------------------------


class AnsweringView(TierListBaseView):
    def get(self, request, pk):
        """Tout ce dont le questionnaire a besoin, en une requête (spec §59)."""
        tier_list = self.get_tier_list(request, pk)
        require_status(
            tier_list,
            TierListStatus.ANSWERING,
            TierListStatus.JOKER,
            TierListStatus.COMPLETED,
            message="Le questionnaire n'a pas encore commencé.",
            code="not_answering",
        )
        participant = get_participant(tier_list, request.user)

        questions = list(tier_list.questions.all())
        progress_rows = (
            ParticipantItemProgress.objects.filter(participant=participant)
            .select_related("item")
            .order_by("display_order", "id")
        )
        answers = Answer.objects.filter(participant=participant).values(
            "item_id", "question_id", "value"
        )
        answers_by_item: dict[int, dict[str, int]] = {}
        for row in answers:
            answers_by_item.setdefault(row["item_id"], {})[str(row["question_id"])] = row["value"]

        items = []
        for row in progress_rows:
            payload = ItemSerializer(row.item, context={"request": request}).data
            payload["display_order"] = row.display_order
            payload["is_validated"] = row.is_validated
            payload["answers"] = answers_by_item.get(row.item_id, {})
            items.append(payload)

        return Response(
            {
                "tier_list": self.serialize(tier_list, request),
                # Le coefficient reste caché pendant le questionnaire (spec §15.3).
                "questions": QuestionForAnsweringSerializer(questions, many=True).data,
                "items": items,
                "progress": participant_progress(participant),
                "participants": all_participants_progress(tier_list, request),
            }
        )


class AnswerWriteView(TierListBaseView):
    def put(self, request, pk, item_id, question_id):
        tier_list = self.get_tier_list(request, pk)
        participant = get_participant(tier_list, request.user)
        item = get_object_or_404(Item, pk=item_id, tier_list=tier_list)
        question = get_object_or_404(Question, pk=question_id, tier_list=tier_list)

        serializer = AnswerWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answer = save_answer(participant, item, question, serializer.validated_data["value"])
        return Response({"item_id": item.pk, "question_id": question.pk, "value": answer.value})


class ItemValidateView(TierListBaseView):
    def post(self, request, pk, item_id):
        tier_list = self.get_tier_list(request, pk)
        participant = get_participant(tier_list, request.user)
        item = get_object_or_404(Item, pk=item_id, tier_list=tier_list)

        validate_item(participant, item)
        participant.refresh_from_db()
        tier_list.refresh_from_db()
        return Response(
            {
                "item_id": item.pk,
                "is_validated": True,
                "progress": participant_progress(participant),
                "tier_list_status": tier_list.status,
            }
        )


# ---------------------------------------------------------------------------
# Résultats
# ---------------------------------------------------------------------------


class RankingView(TierListBaseView):
    def get(self, request, pk):
        tier_list = self.get_tier_list(request, pk)
        require_status(
            tier_list,
            TierListStatus.JOKER,
            TierListStatus.COMPLETED,
            message=(
                "Tout le monde n'a pas terminé. Je pourrais inventer leurs réponses, "
                "mais apparemment ce serait « malhonnête »."
            ),
            code="ranking_not_ready",
        )
        return Response(ranking_payload(tier_list, request))


class ItemResultDetailView(TierListBaseView):
    def get(self, request, pk, item_id):
        tier_list = self.get_tier_list(request, pk)
        require_status(
            tier_list,
            TierListStatus.JOKER,
            TierListStatus.COMPLETED,
            message="Les résultats ne sont pas encore disponibles.",
            code="ranking_not_ready",
        )
        item = get_object_or_404(Item, pk=item_id, tier_list=tier_list)
        return Response(item_result_detail(tier_list, item, request))


# ---------------------------------------------------------------------------
# Joker
# ---------------------------------------------------------------------------


class JokerStateView(TierListBaseView):
    def get(self, request, pk):
        tier_list = self.get_tier_list(request, pk)
        require_status(
            tier_list,
            TierListStatus.JOKER,
            TierListStatus.COMPLETED,
            message="La phase joker n'a pas encore commencé.",
            code="not_joker_phase",
        )
        return Response(self._state(tier_list, request))

    @staticmethod
    def _state(tier_list, request) -> dict:
        from tierlists.models import Item, JokerAction

        participant = get_participant(tier_list, request.user)
        actions = (
            JokerAction.objects.filter(tier_list=tier_list)
            .select_related("participant", "participant__user", "item", "forced_by")
            .order_by("participant__joker_order", "id")
        )
        turn = joker_service.current_turn(tier_list)
        my_action = next((a for a in actions if a.participant_id == participant.pk), None)

        return {
            "status": tier_list.status,
            "is_creator": tier_list.creator_id == request.user.pk,
            "my_participant_id": participant.pk,
            "current_turn": (
                serialize_joker_action(turn, request) if turn is not None else None
            ),
            "is_my_turn": bool(turn and turn.participant_id == participant.pk),
            "my_joker": serialize_joker_action(my_action, request) if my_action else None,
            "order": [serialize_joker_action(action, request) for action in actions],
            "history": [
                serialize_joker_action(action, request)
                for action in sorted(
                    (a for a in actions if a.played_at is not None),
                    key=lambda a: a.played_at,
                )
            ],
            "locked_item_ids": list(
                Item.objects.filter(tier_list=tier_list, joker_locked=True).values_list(
                    "id", flat=True
                )
            ),
            "ranking": ranking_payload(tier_list, request),
        }


class JokerUseView(TierListBaseView):
    def post(self, request, pk):
        tier_list = self.get_tier_list(request, pk)
        serializer = JokerUseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        joker_service.use_joker(
            tier_list,
            request.user,
            serializer.validated_data["item_id"],
            serializer.validated_data["to_rank"],
        )
        tier_list.refresh_from_db()
        return Response(JokerStateView._state(tier_list, request))


class JokerSkipView(TierListBaseView):
    def post(self, request, pk):
        tier_list = self.get_tier_list(request, pk)
        joker_service.skip_joker(tier_list, request.user)
        tier_list.refresh_from_db()
        return Response(JokerStateView._state(tier_list, request))


class JokerForceSkipView(TierListBaseView):
    def post(self, request, pk):
        tier_list = self.get_tier_list(request, pk)
        joker_service.force_skip_joker(tier_list, request.user)
        tier_list.refresh_from_db()
        return Response(JokerStateView._state(tier_list, request))
