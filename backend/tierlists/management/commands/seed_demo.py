"""Jeu de données de démonstration pour le développement local et les tests E2E.

    python manage.py seed_demo

Crée trois comptes actifs (teo, laura, paul) et quatre Tier Lists, une par
statut du cycle de vie, afin de pouvoir ouvrir chaque écran immédiatement.
"""

from __future__ import annotations

import random

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User, UserStatus
from tierlists.constants import REQUIRED_COEFFICIENT_DISTRIBUTION
from tierlists.models import (
    Answer,
    Item,
    Question,
    TierList,
    TierListParticipant,
)
from tierlists.services.jokers import skip_joker, use_joker
from tierlists.services.lifecycle import finalize_tier_list, validate_item

DEMO_PASSWORD = "MotDePasse!42"

QUESTIONS = [
    "Cet item est visuellement réussi.",
    "Cet item est mémorable.",
    "Cet item tient ses promesses.",
    "Cet item vaut son prix.",
    "Cet item est agréable à retrouver.",
    "Cet item mérite d'être recommandé.",
]

FAST_FOODS = ["KFC", "McDonald's", "Burger King", "Quick", "Subway", "Five Guys"]
POKEMON = ["Dracaufeu", "Pikachu", "Ronflex", "Mewtwo", "Bulbizarre", "Magicarpe", "Salamèche"]


class Command(BaseCommand):
    help = "Crée un jeu de données de démonstration (comptes + Tier Lists)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Supprime les Tier Lists de démonstration avant de les recréer.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(42)
        teo = self._user("teo")
        laura = self._user("laura")
        paul = self._user("paul")

        if options["reset"]:
            TierList.objects.filter(creator__in=[teo, laura, paul]).delete()

        draft = self._build(teo, [laura], "Meilleurs fast-foods", "Fast-food", FAST_FOODS[:4])
        self.stdout.write(f"DRAFT      {draft.name} — code {draft.invite_code}")

        answering = self._build(teo, [laura, paul], "Pokémon de départ", "Jeux vidéo", POKEMON[:5])
        finalize_tier_list(answering, teo)
        self._answer_all(answering, laura)
        self.stdout.write(f"ANSWERING  {answering.name} — code {answering.invite_code}")

        joker = self._build(teo, [laura, paul], "Films de Noël", "Cinéma", FAST_FOODS)
        finalize_tier_list(joker, teo)
        for user in (teo, laura, paul):
            self._answer_all(joker, user)
        joker.refresh_from_db()
        self.stdout.write(f"JOKER      {joker.name} — code {joker.invite_code}")

        completed = self._build(teo, [laura], "Jeux vidéo cultes", "Jeux vidéo", POKEMON)
        finalize_tier_list(completed, teo)
        for user in (teo, laura):
            self._answer_all(completed, user)
        completed.refresh_from_db()
        # Laura a fini en dernier : elle joue en premier.
        first_item = completed.scores.order_by("global_score").first().item
        use_joker(completed, laura, first_item.pk, 1)
        skip_joker(completed, teo)
        completed.refresh_from_db()
        self.stdout.write(f"COMPLETED  {completed.name} — code {completed.invite_code}")

        self.stdout.write(
            self.style.SUCCESS(f"\nComptes : teo / laura / paul — mot de passe : {DEMO_PASSWORD}")
        )

    def _user(self, username: str) -> User:
        user, created = User.objects.get_or_create(username=username)
        if created:
            user.set_password(DEMO_PASSWORD)
        user.status = UserStatus.ACTIVE
        user.save()
        return user

    def _build(self, creator: User, others: list[User], name: str, theme: str, items: list[str]):
        tier_list = TierList.objects.create(creator=creator, name=name, theme=theme)
        TierListParticipant.objects.create(tier_list=tier_list, user=creator)
        for user in others:
            TierListParticipant.objects.create(tier_list=tier_list, user=user)

        for index, (text, coefficient) in enumerate(
            zip(QUESTIONS, REQUIRED_COEFFICIENT_DISTRIBUTION, strict=False)
        ):
            Question.objects.create(
                tier_list=tier_list, text=text, coefficient=coefficient, display_order=index + 1
            )
        for item_name in items:
            Item.objects.create(tier_list=tier_list, name=item_name)
        return tier_list

    def _answer_all(self, tier_list: TierList, user: User) -> None:
        participant = tier_list.participants.get(user=user)
        questions = list(tier_list.questions.all())
        for progress in participant.item_progress.select_related("item").all():
            for question in questions:
                Answer.objects.update_or_create(
                    participant=participant,
                    item=progress.item,
                    question=question,
                    defaults={"value": random.randint(1, 9)},
                )
            validate_item(participant, progress.item)
