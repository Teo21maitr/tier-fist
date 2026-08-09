"""Utilisateur Tier Fist (spec §6, §48.1).

Inscription volontairement minimale : username + password, aucune adresse email.
Un compte naît ``PENDING`` et ne peut pas se connecter tant qu'un administrateur
ne l'a pas accepté depuis le Django Admin. Un compte refusé est supprimé, il n'y
a donc pas de statut ``REJECTED``.
"""

from __future__ import annotations

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models

from common.uploads import avatar_upload_to

USERNAME_VALIDATOR = RegexValidator(
    regex=r"^[\w.\-]{3,30}$",
    message=(
        "Le pseudo doit faire entre 3 et 30 caractères et ne contenir que des "
        "lettres, chiffres, tirets, underscores ou points."
    ),
)


class UserStatus(models.TextChoices):
    PENDING = "PENDING", "En attente de validation"
    ACTIVE = "ACTIVE", "Actif"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, username: str, password: str | None = None, **extra):
        if not username:
            raise ValueError("Un pseudo est obligatoire.")
        extra.setdefault("status", UserStatus.PENDING)
        user = self.model(username=username, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username: str, password: str | None = None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        # Un superutilisateur doit pouvoir se connecter immédiatement.
        extra["status"] = UserStatus.ACTIVE
        if extra.get("is_staff") is not True or extra.get("is_superuser") is not True:
            raise ValueError("Un superutilisateur doit avoir is_staff et is_superuser.")
        return self.create_user(username, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(
        "pseudo",
        max_length=30,
        unique=True,
        validators=[USERNAME_VALIDATOR],
        error_messages={"unique": "Ce pseudo est déjà pris. Laurent compatit."},
    )
    status = models.CharField(
        "statut",
        max_length=10,
        choices=UserStatus.choices,
        default=UserStatus.PENDING,
        db_index=True,
    )
    avatar = models.ImageField("avatar", upload_to=avatar_upload_to, blank=True, null=True)
    is_staff = models.BooleanField("accès admin", default=False)
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        ordering = ["username"]

    def __str__(self) -> str:
        return self.username

    @property
    def is_active(self) -> bool:
        """Django refuse l'authentification des utilisateurs non actifs.

        C'est ce qui empêche un compte ``PENDING`` de se connecter (spec §6.1).
        """
        return self.status == UserStatus.ACTIVE

    def approve(self) -> None:
        self.status = UserStatus.ACTIVE
        self.save(update_fields=["status", "updated_at"])
