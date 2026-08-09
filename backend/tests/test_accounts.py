"""Comptes : inscription PENDING, validation admin, connexion, profil (spec §6)."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from accounts.models import User, UserStatus

pytestmark = pytest.mark.django_db


def test_inscription_cree_un_compte_pending(api):
    response = api.post(
        "/api/auth/register", {"username": "teo", "password": "MotDePasse!42"}, format="json"
    )
    assert response.status_code == 201
    user = User.objects.get(username="teo")
    assert user.status == UserStatus.PENDING
    assert not user.is_active


def test_aucune_adresse_email_n_est_demandee(api):
    """L'inscription est volontairement minimale : username + password."""
    response = api.post(
        "/api/auth/register", {"username": "laura", "password": "MotDePasse!42"}, format="json"
    )
    assert response.status_code == 201
    assert not hasattr(User.objects.get(username="laura"), "email")


def test_un_compte_pending_ne_peut_pas_se_connecter(api):
    api.post("/api/auth/register", {"username": "teo", "password": "MotDePasse!42"}, format="json")
    response = api.post(
        "/api/auth/login", {"username": "teo", "password": "MotDePasse!42"}, format="json"
    )
    assert response.status_code == 403
    assert response.data["code"] == "account_pending"


def test_un_compte_accepte_peut_se_connecter(api):
    api.post("/api/auth/register", {"username": "teo", "password": "MotDePasse!42"}, format="json")
    user = User.objects.get(username="teo")
    user.approve()

    response = api.post(
        "/api/auth/login", {"username": "teo", "password": "MotDePasse!42"}, format="json"
    )
    assert response.status_code == 200
    assert response.data["username"] == "teo"
    assert "_auth_user_id" in api.session


def test_le_token_de_session_est_un_cookie_httponly(api, teo):
    response = api.post(
        "/api/auth/login", {"username": "teo", "password": "MotDePasse!42"}, format="json"
    )
    cookie = response.cookies["tierfist_session"]
    assert cookie["httponly"] is True


def test_mauvais_mot_de_passe(api, teo):
    response = api.post(
        "/api/auth/login", {"username": "teo", "password": "faux"}, format="json"
    )
    assert response.status_code == 400
    assert response.data["code"] == "invalid_credentials"


def test_username_unique(api, teo):
    response = api.post(
        "/api/auth/register", {"username": "TEO", "password": "MotDePasse!42"}, format="json"
    )
    assert response.status_code == 400


def test_mot_de_passe_trop_faible_refuse(api):
    response = api.post("/api/auth/register", {"username": "teo", "password": "1234"}, format="json")
    assert response.status_code == 400


def test_me_necessite_une_authentification(api):
    assert api.get("/api/auth/me").status_code == 403


def test_me_renvoie_le_profil(auth_client, teo):
    response = auth_client(teo).get("/api/auth/me")
    assert response.status_code == 200
    assert response.data["username"] == "teo"
    # Avatar par défaut : première lettre du pseudo (spec §6.4).
    assert response.data["initial"] == "T"
    assert response.data["avatar_url"] is None


def test_changement_de_username(auth_client, teo):
    response = auth_client(teo).patch("/api/auth/me", {"username": "teo2"}, format="json")
    assert response.status_code == 200
    teo.refresh_from_db()
    assert teo.username == "teo2"


def test_username_deja_pris_refuse(auth_client, teo, laura):
    response = auth_client(teo).patch("/api/auth/me", {"username": "laura"}, format="json")
    assert response.status_code == 400


def test_upload_avatar(auth_client, teo, png_upload):
    response = auth_client(teo).patch(
        "/api/auth/me", {"avatar": png_upload()}, format="multipart"
    )
    assert response.status_code == 200
    assert response.data["avatar_url"] is not None
    teo.refresh_from_db()
    # Le nom du fichier est généré côté serveur (spec §51).
    assert "photo" not in teo.avatar.name
    teo.avatar.delete(save=True)


def test_fichier_non_image_refuse(auth_client, teo):
    from django.core.files.uploadedfile import SimpleUploadedFile

    fake = SimpleUploadedFile("virus.png", b"pas du tout une image", content_type="image/png")
    response = auth_client(teo).patch("/api/auth/me", {"avatar": fake}, format="multipart")
    assert response.status_code == 400


def test_suppression_avatar(auth_client, teo, png_upload):
    client = auth_client(teo)
    client.patch("/api/auth/me", {"avatar": png_upload()}, format="multipart")
    response = client.patch("/api/auth/me", {"remove_avatar": True}, format="json")
    assert response.status_code == 200
    assert response.data["avatar_url"] is None


def test_changement_de_mot_de_passe(auth_client, teo):
    response = auth_client(teo).post(
        "/api/auth/change-password",
        {"current_password": "MotDePasse!42", "new_password": "NouveauSecret!77"},
        format="json",
    )
    assert response.status_code == 200
    teo.refresh_from_db()
    assert teo.check_password("NouveauSecret!77")


def test_changement_de_mot_de_passe_exige_l_ancien(auth_client, teo):
    response = auth_client(teo).post(
        "/api/auth/change-password",
        {"current_password": "faux", "new_password": "NouveauSecret!77"},
        format="json",
    )
    assert response.status_code == 400


def test_logout(api, teo):
    api.post("/api/auth/login", {"username": "teo", "password": "MotDePasse!42"}, format="json")
    assert api.post("/api/auth/logout").status_code == 204
    assert api.get("/api/auth/me").status_code == 403


def test_csrf_est_exige_sur_les_requetes_mutantes(teo):
    """La protection CSRF est active (spec §6.2, §51)."""
    client = APIClient(enforce_csrf_checks=True)
    client.post("/api/auth/login", {"username": "teo", "password": "MotDePasse!42"}, format="json")
    # Session ouverte mais requête mutante sans en-tête CSRF -> refusée.
    response = client.post("/api/tier-lists", {"name": "X", "theme": "Y"}, format="json")
    assert response.status_code == 403


def test_csrf_avec_le_bon_token_passe(teo):
    client = APIClient(enforce_csrf_checks=True)
    client.get("/api/auth/csrf")
    token = client.cookies["tierfist_csrftoken"].value
    client.post(
        "/api/auth/login",
        {"username": "teo", "password": "MotDePasse!42"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    token = client.cookies["tierfist_csrftoken"].value
    response = client.post(
        "/api/tier-lists",
        {"name": "Fast-food", "theme": "Fast-food"},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 201
