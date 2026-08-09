"""Constantes métier figées par la spécification (§72).

Ces valeurs ne doivent jamais être « assouplies » pour simplifier le code.
"""

from django.db import models

# --- Rangs (spec §13) ------------------------------------------------------
RANK_COUNT = 5
RANK_NUMBERS = (1, 2, 3, 4, 5)
DEFAULT_RANK_NAMES = ("S", "A", "B", "C", "D")
# Couleurs fixes, non personnalisables. Exposées à titre indicatif : le
# frontend les applique via ses propres classes.
RANK_COLORS = ("red", "orange", "yellow", "green", "blue")
RANK_FIELD_NAMES = tuple(f"rank_{number}_name" for number in RANK_NUMBERS)

# --- Questions (spec §15) --------------------------------------------------
REQUIRED_QUESTION_COUNT = 6
# Distribution exacte imposée : 1, 1, 2, 2, 3, 5 (somme = 14).
REQUIRED_COEFFICIENT_DISTRIBUTION = (1, 1, 2, 2, 3, 5)
ALLOWED_COEFFICIENTS = (1, 2, 3, 5)
COEFFICIENT_SLOTS = {1: 2, 2: 2, 3: 1, 5: 1}
COEFFICIENT_TOTAL = sum(REQUIRED_COEFFICIENT_DISTRIBUTION)  # 14

# --- Réponses (spec §19) ---------------------------------------------------
MIN_ANSWER_VALUE = 1
MAX_ANSWER_VALUE = 9
NEUTRAL_ANSWER_VALUE = 5

# --- Code d'invitation (spec §9.1) -----------------------------------------
INVITE_CODE_LENGTH = 6
# Alphabet sans caractères ambigus : ni 0/O, ni 1/I.
INVITE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

# --- Classement (spec §27.2) -----------------------------------------------
S_RANK_TARGET_RATIO_PERCENT = 10


class TierListStatus(models.TextChoices):
    DRAFT = "DRAFT", "En création"
    ANSWERING = "ANSWERING", "Questionnaire en cours"
    JOKER = "JOKER", "Phase joker"
    COMPLETED = "COMPLETED", "Terminée"


class JokerStatus(models.TextChoices):
    PENDING = "PENDING", "En attente"
    USED = "USED", "Utilisé"
    SKIPPED = "SKIPPED", "Abandonné"
    FORCED_SKIP = "FORCED_SKIP", "Tour forcé par le créateur"


TERMINAL_JOKER_STATUSES = (
    JokerStatus.USED,
    JokerStatus.SKIPPED,
    JokerStatus.FORCED_SKIP,
)
