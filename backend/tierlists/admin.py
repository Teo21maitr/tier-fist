"""Django Admin des Tier Lists (spec §56) : consultation et diagnostic."""

from django.contrib import admin

from tierlists.models import (
    Answer,
    Item,
    ItemScore,
    JokerAction,
    ParticipantItemProgress,
    Question,
    TierList,
    TierListParticipant,
)


class ParticipantInline(admin.TabularInline):
    model = TierListParticipant
    extra = 0
    readonly_fields = [
        "user",
        "joined_at",
        "answering_completed_at",
        "joker_order",
        "answer_order_seed",
    ]
    can_delete = False


class ItemInline(admin.TabularInline):
    model = Item
    extra = 0
    fields = ["name", "external_image_url", "uploaded_image", "joker_locked"]
    readonly_fields = ["joker_locked"]


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ["display_order", "text", "coefficient"]


@admin.register(TierList)
class TierListAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "theme",
        "invite_code",
        "status",
        "creator",
        "participants_count",
        "items_count",
        "updated_at",
    ]
    list_filter = ["status"]
    search_fields = ["name", "theme", "invite_code", "creator__username"]
    readonly_fields = ["invite_code", "created_at", "updated_at", "finalized_at", "completed_at"]
    inlines = [ParticipantInline, QuestionInline, ItemInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("creator")

    @admin.display(description="participants")
    def participants_count(self, obj: TierList) -> int:
        return obj.participants.count()

    @admin.display(description="items")
    def items_count(self, obj: TierList) -> int:
        return obj.items.count()


@admin.register(ItemScore)
class ItemScoreAdmin(admin.ModelAdmin):
    list_display = [
        "item", "tier_list", "global_score",
        "algorithm_rank", "current_rank", "final_rank",
    ]
    list_filter = ["tier_list"]
    readonly_fields = [field.name for field in ItemScore._meta.fields]


@admin.register(JokerAction)
class JokerActionAdmin(admin.ModelAdmin):
    list_display = [
        "tier_list", "participant", "status",
        "item", "from_rank", "to_rank", "played_at",
    ]
    list_filter = ["status", "tier_list"]
    readonly_fields = [field.name for field in JokerAction._meta.fields]


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ["participant", "item", "question", "value", "updated_at"]
    list_filter = ["participant__tier_list"]
    readonly_fields = [field.name for field in Answer._meta.fields]


admin.site.register(ParticipantItemProgress)
admin.site.register(TierListParticipant)
