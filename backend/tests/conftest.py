"""Fixtures partagées par les tests backend."""

from __future__ import annotations

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from accounts.models import User, UserStatus
from tierlists.constants import REQUIRED_COEFFICIENT_DISTRIBUTION
from tierlists.models import Item, Question, TierList, TierListParticipant


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def make_user(db):
    def _make(username: str = "teo", password: str = "MotDePasse!42", active: bool = True):
        user = User.objects.create_user(username=username, password=password)
        if active:
            user.status = UserStatus.ACTIVE
            user.save(update_fields=["status"])
        return user

    return _make


@pytest.fixture
def teo(make_user):
    return make_user("teo")


@pytest.fixture
def laura(make_user):
    return make_user("laura")


@pytest.fixture
def paul(make_user):
    return make_user("paul")


@pytest.fixture
def auth_client(api):
    def _login(user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    return _login


@pytest.fixture
def make_tier_list(db):
    def _make(creator, name: str = "Fast-food", theme: str = "Fast-food", **kwargs):
        tier_list = TierList.objects.create(
            creator=creator, name=name, theme=theme, **kwargs
        )
        TierListParticipant.objects.create(tier_list=tier_list, user=creator)
        return tier_list

    return _make


@pytest.fixture
def join(db):
    def _join(tier_list, user):
        return TierListParticipant.objects.create(tier_list=tier_list, user=user)

    return _join


@pytest.fixture
def add_items(db):
    def _add(tier_list, names):
        return [Item.objects.create(tier_list=tier_list, name=name) for name in names]

    return _add


@pytest.fixture
def add_valid_questions(db):
    """Crée les six questions avec la distribution imposée 1,1,2,2,3,5."""

    def _add(tier_list):
        return [
            Question.objects.create(
                tier_list=tier_list,
                text=f"Cet item est réussi sur le critère {index + 1}.",
                coefficient=coefficient,
                display_order=index + 1,
            )
            for index, coefficient in enumerate(REQUIRED_COEFFICIENT_DISTRIBUTION)
        ]

    return _add


@pytest.fixture
def png_upload():
    """Petit PNG valide généré par Pillow, pour tester les uploads."""

    def _make(name: str = "photo.png"):
        from PIL import Image

        buffer = io.BytesIO()
        Image.new("RGB", (8, 8), (200, 30, 30)).save(buffer, format="PNG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")

    return _make
