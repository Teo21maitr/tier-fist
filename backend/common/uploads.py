"""Gestion sécurisée des images uploadées (spec §14.2, §51).

Règles appliquées :
- le nom de fichier fourni par le client n'est jamais utilisé ;
- le nom est généré côté serveur (uuid4), ce qui neutralise le path traversal ;
- le contenu est vérifié via Pillow, pas seulement l'extension ni le Content-Type ;
- une taille maximale technique configurable protège d'un déni de service.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError

# Formats Pillow acceptés -> extension normalisée côté serveur.
ALLOWED_IMAGE_FORMATS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "GIF": ".gif",
    "WEBP": ".webp",
}


def _upload_to(folder: str, filename: str) -> str:
    extension = ""
    if "." in filename:
        extension = "." + filename.rsplit(".", 1)[1].lower()
    if extension not in ALLOWED_IMAGE_FORMATS.values():
        extension = ".img"
    return f"{folder}/{uuid.uuid4().hex}{extension}"


def avatar_upload_to(instance, filename: str) -> str:
    return _upload_to("avatars", filename)


def item_image_upload_to(instance, filename: str) -> str:
    return _upload_to("items", filename)


def validate_image_upload(uploaded_file):
    """Valide un fichier image uploadé et renvoie son extension normalisée.

    Lève une ``ValidationError`` avec un message directement affichable.
    """
    max_size = settings.MAX_UPLOAD_IMAGE_SIZE
    if uploaded_file.size > max_size:
        limit_mb = max_size / (1024 * 1024)
        raise ValidationError(
            f"Cette image est trop lourde (limite technique : {limit_mb:.0f} Mo)."
        )

    try:
        from PIL import Image

        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        image.verify()
        image_format = (image.format or "").upper()
    except Exception as exc:
        raise ValidationError(
            "Ce fichier n'est pas une image valide. Laurent a regardé, il est formel."
        ) from exc
    finally:
        uploaded_file.seek(0)

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError(
            "Format d'image non supporté. Utilise JPEG, PNG, GIF ou WebP."
        )
    return ALLOWED_IMAGE_FORMATS[image_format]


def normalize_uploaded_image_name(uploaded_file, extension: str) -> None:
    """Force un nom de fichier généré côté serveur, cohérent avec le vrai format."""
    uploaded_file.name = f"{uuid.uuid4().hex}{extension}"
