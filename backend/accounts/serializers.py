from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from accounts.models import User, UserStatus
from common.uploads import prepare_image_upload


class UserSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    initial = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "status", "avatar_url", "initial", "is_staff"]
        read_only_fields = fields

    def get_avatar_url(self, obj: User) -> str | None:
        if not obj.avatar:
            return None
        request = self.context.get("request")
        url = obj.avatar.url
        return request.build_absolute_uri(url) if request else url

    def get_initial(self, obj: User) -> str:
        """Avatar par défaut : première lettre du pseudo (spec §6.4)."""
        return obj.username[:1].upper()


class PublicUserSerializer(UserSerializer):
    """Vue d'un autre utilisateur : pas d'information de statut ni de rôle."""

    class Meta(UserSerializer.Meta):
        fields = ["id", "username", "avatar_url", "initial"]
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=30)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_username(self, value: str) -> str:
        value = value.strip()
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Ce pseudo est déjà pris. Laurent compatit.")
        return value

    def validate_password(self, value: str) -> str:
        try:
            password_validation.validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    def create(self, validated_data) -> User:
        user = User(username=validated_data["username"], status=UserStatus.PENDING)
        user.full_clean(exclude=["password"])
        user.set_password(validated_data["password"])
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Mot de passe actuel incorrect.")
        return value

    def validate_new_password(self, value: str) -> str:
        try:
            password_validation.validate_password(value, self.context["request"].user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value


class ProfileUpdateSerializer(serializers.ModelSerializer):
    # Permet de supprimer explicitement l'avatar depuis le frontend.
    remove_avatar = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = User
        fields = ["username", "avatar", "remove_avatar"]
        extra_kwargs = {
            "username": {"required": False},
            "avatar": {"required": False, "allow_null": True},
        }

    def validate_username(self, value: str) -> str:
        value = value.strip()
        if (
            User.objects.filter(username__iexact=value)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise serializers.ValidationError("Ce pseudo est déjà pris. Laurent compatit.")
        return value

    def validate_avatar(self, value):
        if value in (None, ""):
            return value
        try:
            # Renvoie le fichier prêt à stocker : un HEIC est converti en JPEG.
            return prepare_image_upload(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc

    def update(self, instance: User, validated_data) -> User:
        if validated_data.pop("remove_avatar", False):
            if instance.avatar:
                instance.avatar.delete(save=False)
            instance.avatar = None
        elif "avatar" in validated_data and validated_data["avatar"] and instance.avatar:
            # Remplacement : on supprime l'ancien fichier pour ne pas polluer le volume.
            instance.avatar.delete(save=False)
        return super().update(instance, validated_data)
