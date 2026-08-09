import logging

from django.contrib.auth import login, logout, update_session_auth_hash
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User, UserStatus
from accounts.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
)

logger = logging.getLogger("tierfist")


@method_decorator(ensure_csrf_cookie, name="get")
class CsrfView(APIView):
    """Pose le cookie CSRF avant tout appel mutant du SPA."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrf_token": get_token(request)})


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        logger.info("Nouvelle demande de compte: %s (id=%s)", user.username, user.pk)
        return Response(
            {
                "detail": (
                    "Compte créé. Un administrateur doit le valider avant que tu "
                    "puisses te connecter."
                ),
                "status": user.status,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"].strip()
        password = serializer.validated_data["password"]

        user = User.objects.filter(username__iexact=username).first()
        if user is None or not user.check_password(password):
            return Response(
                {"detail": "Pseudo ou mot de passe incorrect.", "code": "invalid_credentials"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user.status != UserStatus.ACTIVE:
            return Response(
                {
                    "detail": (
                        "Ton compte attend encore la validation d'un administrateur. "
                        "Laurent surveille la file d'attente."
                    ),
                    "code": "account_pending",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response(UserSerializer(user, context={"request": request}).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user, context={"request": request}).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user, context={"request": request}).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        # Conserve la session active après changement de mot de passe.
        update_session_auth_hash(request, user)
        return Response({"detail": "Mot de passe mis à jour."})
