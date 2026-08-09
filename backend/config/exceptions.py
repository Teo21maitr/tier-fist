"""Normalisation des erreurs API.

Toutes les erreurs renvoyées au frontend suivent la même forme :

    {"detail": "message lisible en français", "code": "slug_optionnel"}

Cela permet au frontend d'afficher les messages de Laurent Baffist (spec §54)
sans avoir à deviner la structure de la réponse.
"""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions
from rest_framework.views import exception_handler as drf_exception_handler


class BusinessError(exceptions.APIException):
    """Erreur de règle métier, renvoyée en 400 avec un code exploitable."""

    status_code = 400
    default_detail = "Action impossible."
    default_code = "business_error"

    def __init__(self, detail=None, code=None, status_code=None):
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail=detail, code=code)


class Conflict(BusinessError):
    status_code = 409
    default_detail = "Conflit avec l'état actuel de la Tier List."
    default_code = "conflict"


def tierfist_exception_handler(exc, context):
    if isinstance(exc, Http404):
        exc = exceptions.NotFound("Ressource introuvable.")
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied("Tu n'as pas accès à cette ressource.")

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    code = getattr(exc, "default_code", None)
    detail = exc.detail if hasattr(exc, "detail") else None

    if isinstance(detail, str):
        payload = {"detail": str(detail), "code": getattr(detail, "code", code)}
    elif isinstance(detail, list):
        payload = {"detail": " ".join(str(item) for item in detail), "code": code}
    elif isinstance(detail, dict):
        # Erreurs de validation champ par champ : on garde le détail complet et
        # on expose en plus un message principal directement affichable.
        payload = {"errors": _stringify(detail), "code": code or "validation_error"}
        payload["detail"] = _first_message(payload["errors"])
    else:
        payload = {"detail": "Une erreur est survenue.", "code": code}

    response.data = payload
    return response


def _stringify(detail):
    if isinstance(detail, dict):
        return {key: _stringify(value) for key, value in detail.items()}
    if isinstance(detail, list):
        return [_stringify(value) for value in detail]
    return str(detail)


def _first_message(errors):
    if isinstance(errors, dict):
        for value in errors.values():
            message = _first_message(value)
            if message:
                return message
        return ""
    if isinstance(errors, list):
        for value in errors:
            message = _first_message(value)
            if message:
                return message
        return ""
    return str(errors)
