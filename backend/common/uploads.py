"""Gestion sécurisée des images uploadées (spec §14.2, §51).

Règles appliquées :
- le nom de fichier fourni par le client n'est jamais utilisé ;
- le nom est généré côté serveur (uuid4), ce qui neutralise le path traversal ;
- le contenu est vérifié via Pillow, pas seulement l'extension ni le Content-Type ;
- une taille maximale technique configurable protège d'un déni de service ;
- les photos HEIC (format par défaut des iPhone) sont converties en JPEG, car
  Chrome et Firefox ne savent pas les afficher.
"""

from __future__ import annotations

import uuid
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

# Formats stockés tels quels -> extension normalisée côté serveur.
ALLOWED_IMAGE_FORMATS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "GIF": ".gif",
    "WEBP": ".webp",
}

# Formats acceptés à l'upload mais convertis en JPEG avant stockage.
# Pillow expose les fichiers .heic/.heif sous le format « HEIF ».
CONVERTED_IMAGE_FORMATS = {"HEIF", "HEIC"}

# Libellé unique, réutilisé dans les messages d'erreur et la documentation.
SUPPORTED_FORMATS_LABEL = "JPEG, PNG, GIF, WebP ou HEIC"

_heif_registered = False


def register_heif_opener() -> None:
    """Branche le décodeur HEIF sur Pillow, une seule fois par processus.

    Doit impérativement être appelé au démarrage, avant toute requête : le champ
    ``ImageField`` de Django valide l'image *avant* nos propres validateurs. Sans
    décodeur enregistré à ce moment-là, un HEIC serait refusé comme « fichier
    corrompu » et n'atteindrait jamais la conversion en JPEG.
    """
    global _heif_registered
    if _heif_registered:
        return
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except ImportError:  # pragma: no cover - dépendance déclarée dans requirements
        pass
    _heif_registered = True


# Ce module est importé par les modèles (upload_to), donc pendant django.setup() :
# le décodeur est branché avant que la moindre requête ne soit servie.
register_heif_opener()


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


def prepare_image_upload(uploaded_file):
    """Valide un fichier uploadé et renvoie le fichier prêt à être stocké.

    - refuse ce qui n'est pas une image, quel que soit le nom ou le Content-Type ;
    - refuse les fichiers dépassant la limite technique configurée ;
    - convertit le HEIC en JPEG ;
    - renomme systématiquement le fichier côté serveur.

    Lève une ``ValidationError`` dont le message est directement affichable.
    """
    max_size = settings.MAX_UPLOAD_IMAGE_SIZE
    if uploaded_file.size > max_size:
        limit_mb = max_size / (1024 * 1024)
        raise ValidationError(
            f"Cette image est trop lourde (limite technique : {limit_mb:.0f} Mo)."
        )

    register_heif_opener()
    from PIL import Image

    # verify() consomme l'objet image : on l'utilise uniquement pour identifier
    # le format, puis on rouvre le fichier si une conversion est nécessaire.
    try:
        uploaded_file.seek(0)
        probe = Image.open(uploaded_file)
        probe.verify()
        image_format = (probe.format or "").upper()
    except Exception as exc:
        raise ValidationError(
            "Ce fichier n'est pas une image valide. Laurent a regardé, il est formel."
        ) from exc
    finally:
        uploaded_file.seek(0)

    if image_format in CONVERTED_IMAGE_FORMATS:
        return _convert_to_jpeg(uploaded_file)

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError(
            f"Format d'image non supporté. Utilise {SUPPORTED_FORMATS_LABEL}."
        )

    uploaded_file.name = f"{uuid.uuid4().hex}{ALLOWED_IMAGE_FORMATS[image_format]}"
    return uploaded_file


def _convert_to_jpeg(uploaded_file):
    """Convertit une photo HEIC en JPEG affichable par tous les navigateurs."""
    from PIL import Image, ImageOps

    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        # Les photos de téléphone portent leur orientation en EXIF. Le JPEG
        # produit ne conserve pas ces métadonnées : on applique la rotation.
        image = ImageOps.exif_transpose(image)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=90, optimize=True)
    except Exception as exc:
        raise ValidationError(
            "Cette photo n'a pas pu être convertie. Réessaie avec un JPEG ou un PNG."
        ) from exc
    finally:
        uploaded_file.seek(0)

    buffer.seek(0)
    return ContentFile(buffer.read(), name=f"{uuid.uuid4().hex}.jpg")
