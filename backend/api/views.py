from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view
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
        CampfireEvent.objects.select_related("club", "club__creator", "creator")
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
    club = CampfireClub.objects.select_related("creator").get(pk=club.pk)
    serializer = CampfireClubSerializer(club, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)
