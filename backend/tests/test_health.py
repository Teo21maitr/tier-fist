"""Sonde de santé : elle conditionne la mise en ligne d'un déploiement Railway."""

import pytest
from django.conf import settings

pytestmark = pytest.mark.django_db


def test_la_sonde_repond_ok(api):
    response = api.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_la_sonde_est_accessible_sans_authentification(api):
    assert api.get("/healthz").status_code == 200


def test_la_sonde_accepte_l_hote_de_la_sonde_railway(api):
    """Railway interroge le conteneur avec Host: healthcheck.railway.app."""
    assert "healthcheck.railway.app" in settings.ALLOWED_HOSTS
    response = api.get("/healthz", HTTP_HOST="healthcheck.railway.app")
    assert response.status_code == 200


def test_la_sonde_est_exemptee_de_la_redirection_https():
    """Sans cette exemption, tous les déploiements échoueraient en 301."""
    from config import settings as settings_module

    exempt = getattr(settings_module, "SECURE_REDIRECT_EXEMPT", None)
    # En développement (DEBUG=True) la redirection n'est pas active du tout.
    if settings_module.DEBUG:
        pytest.skip("La redirection HTTPS n'est active qu'en production.")
    assert exempt == [r"^healthz$"]
