from __future__ import annotations

from django.contrib.auth import authenticate, get_user_model

from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from campfire import CampfireError

from .models import CampfireClub, CampfireEvent, CampfireToken
from .serializers import (
    CampfireClubSerializer,
    CampfireEventSerializer,
    CampfireTokenSerializer,
)
from .services.campfire import build_campfire_client, get_campfire_config
from .services.importers import persist_club, persist_event
from .services.lookups import ClubLookupError, normalize_club_lookup
from .services.tokens import InvalidCampfireToken, parse_campfire_token

User = get_user_model()


@api_view(["GET"])
def health(_request):
    """Simple health check endpoint the frontend can call."""
    return Response({"status": "ok"})


@api_view(["GET"])
def campfire_config(_request):
    """Expose the Campfire client configuration so the frontend can inspect it."""
    cfg = get_campfire_config()
    return Response(
        {
            "every_seconds": cfg.every.total_seconds(),
            "burst": cfg.burst,
            "max_retries": cfg.max_retries,
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def register_user(request):
    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    if not username or not password:
        return Response({"detail": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)
    if len(password) < 8:
        return Response({"detail": "Password must be at least 8 characters long."}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(username=username).exists():
        return Response({"detail": "Username already taken."}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, password=password)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"username": user.username, "token": token.key}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_user(request):
    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    if not username or not password:
        return Response({"detail": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request, username=username, password=password)
    if not user:
        return Response({"detail": "Invalid credentials."}, status=status.HTTP_400_BAD_REQUEST)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"username": user.username, "token": token.key}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_user(request):
    token = getattr(request, "auth", None)
    if isinstance(token, Token):
        token.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
def campfire_import_event(request):
    """Import a Campfire event (by ID or URL) and persist it locally."""
    reference = (request.data.get("event") or "").strip()
    if not reference:
        return Response({"detail": "Provide an event ID or meetup URL."}, status=status.HTTP_400_BAD_REQUEST)

    client = build_campfire_client()
    try:
        if reference.startswith("http://") or reference.startswith("https://"):
            event_data = client.resolve_event(reference)
        else:
            event_data = client.get_event(reference)
    except CampfireError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    event = persist_event(event_data)
    event = (
        CampfireEvent.objects.select_related("club", "club__creator", "club__owner", "creator")
        .prefetch_related("rsvps__member")
        .get(pk=event.pk)
    )

    serializer = CampfireEventSerializer(event, context={"request": request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(["GET", "POST"])
def campfire_tokens(request):
    """List valid Campfire tokens or allow a new JWT to be registered."""
    if request.method == "POST":
        token_value = (request.data.get("token") or "").strip()
        if not token_value:
            return Response({"detail": "Provide a token."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            decoded = parse_campfire_token(token_value)
        except InvalidCampfireToken as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        token_obj, created = CampfireToken.objects.update_or_create(
            token=decoded.token,
            defaults={
                "email": decoded.email,
                "expires_at": decoded.expires_at,
            },
        )
        serializer = CampfireTokenSerializer(token_obj, context={"request": request})
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=status_code)

    tokens = CampfireToken.objects.valid()
    serializer = CampfireTokenSerializer(tokens, many=True, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def campfire_lookup_club(request):
    """Resolve a Campfire club by URL or ID and return the stored representation."""
    tracker_input = (request.query_params.get("club") or request.query_params.get("query") or "").strip()
    club_url: str | None = None
    club_id: str | None = None

    try:
        if tracker_input:
            club_url, club_id = normalize_club_lookup(tracker_input, strict=True)
        else:
            club_url, club_id = normalize_club_lookup(
                request.query_params.get("url", ""),
                default_kind="url",
            )
            if not club_url and not club_id:
                club_url, club_id = normalize_club_lookup(
                    request.query_params.get("id", ""),
                    default_kind="id",
                )
    except ClubLookupError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    if not club_url and not club_id:
        return Response(
            {"detail": "Provide ?club=, ?url=, or ?id= to lookup a club."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    client = build_campfire_client()
    try:
        club_data = client.resolve_club(club_url) if club_url else client.get_club(club_id or "")
    except CampfireError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    club = persist_club(club_data)
    club = CampfireClub.objects.select_related("creator", "owner").get(pk=club.pk)

    if club.owner_id and club.owner_id != request.user.id:
        return Response(
            {"detail": "This club is already managed by another user."},
            status=status.HTTP_403_FORBIDDEN,
        )

    owned_club = _get_user_owned_club(request.user)
    if owned_club and owned_club.id != club.id:
        return Response(
            {"detail": f"You already manage the club '{owned_club.name}'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not club.owner_id:
        club.owner = request.user
        club.save(update_fields=["owner"])

    serializer = CampfireClubSerializer(club, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
def campfire_import_club_history(request):
    """Import all historical meetups for a club."""
    reference = (request.data.get("club") or "").strip()
    if not reference:
        return Response({"detail": "Provide a club reference."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        club_url, club_id = normalize_club_lookup(reference, strict=True)
    except ClubLookupError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    client = build_campfire_client()
    try:
        if club_url:
            club_data = client.resolve_club(club_url)
            club_id = club_data.id
        else:
            club_data = client.get_club(club_id or "")
    except CampfireError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    try:
        events = client.get_past_meetups(club_id or club_data.id)
    except CampfireError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    imported_ids: list[str] = []
    for event in events:
        persist_event(event)
        imported_ids.append(event.id)

    club = persist_club(club_data)
    club = CampfireClub.objects.select_related("creator", "owner").get(pk=club.pk)
    serializer = CampfireClubSerializer(club, context={"request": request})

    return Response(
        {
            "club": serializer.data,
            "events_imported": len(imported_ids),
            "event_ids": imported_ids,
        },
        status=status.HTTP_200_OK,
    )


def _get_user_owned_club(user):
    if not user.is_authenticated:
        return None
    try:
        return user.campfire_club
    except CampfireClub.DoesNotExist:
        return None
