from django.urls import path

from tierlists import views

urlpatterns = [
    # Tier Lists
    path("tier-lists", views.TierListCollectionView.as_view(), name="tierlist-collection"),
    path("tier-lists/join", views.TierListJoinView.as_view(), name="tierlist-join"),
    path("tier-lists/<int:pk>", views.TierListDetailView.as_view(), name="tierlist-detail"),
    path(
        "tier-lists/<int:pk>/finalize",
        views.TierListFinalizeView.as_view(),
        name="tierlist-finalize",
    ),
    path(
        "tier-lists/<int:pk>/duplicate",
        views.TierListDuplicateView.as_view(),
        name="tierlist-duplicate",
    ),
    path(
        "tier-lists/<int:pk>/participants",
        views.TierListParticipantsView.as_view(),
        name="tierlist-participants",
    ),
    # Items
    path("tier-lists/<int:pk>/items", views.ItemCollectionView.as_view(), name="item-collection"),
    path(
        "tier-lists/<int:pk>/items/<int:item_id>",
        views.ItemDetailView.as_view(),
        name="item-detail",
    ),
    # Questions
    path(
        "tier-lists/<int:pk>/questions",
        views.QuestionCollectionView.as_view(),
        name="question-collection",
    ),
    path(
        "tier-lists/<int:pk>/questions/<int:question_id>",
        views.QuestionDetailView.as_view(),
        name="question-detail",
    ),
    # Questionnaire
    path("tier-lists/<int:pk>/answering", views.AnsweringView.as_view(), name="answering"),
    path(
        "tier-lists/<int:pk>/items/<int:item_id>/answers/<int:question_id>",
        views.AnswerWriteView.as_view(),
        name="answer-write",
    ),
    path(
        "tier-lists/<int:pk>/items/<int:item_id>/validate",
        views.ItemValidateView.as_view(),
        name="item-validate",
    ),
    # Résultats
    path("tier-lists/<int:pk>/ranking", views.RankingView.as_view(), name="ranking"),
    path(
        "tier-lists/<int:pk>/items/<int:item_id>/result-detail",
        views.ItemResultDetailView.as_view(),
        name="item-result-detail",
    ),
    # Joker
    path("tier-lists/<int:pk>/joker", views.JokerStateView.as_view(), name="joker-state"),
    path("tier-lists/<int:pk>/joker/use", views.JokerUseView.as_view(), name="joker-use"),
    path("tier-lists/<int:pk>/joker/skip", views.JokerSkipView.as_view(), name="joker-skip"),
    path(
        "tier-lists/<int:pk>/joker/force-skip",
        views.JokerForceSkipView.as_view(),
        name="joker-force-skip",
    ),
]
