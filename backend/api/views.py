from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from campfire import CampfireError

from .models import CampfireClub, CampfireEvent
from .serializers import CampfireClubSerializer, CampfireEventSerializer
from .services.campfire import build_campfire_client, get_campfire_config
from .services.importers import persist_club, persist_event


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


@api_view(["GET"])
def campfire_lookup_club(request):
    """Resolve a Campfire club by URL or ID and return the stored representation."""
    club_url = request.query_params.get("url", "").strip()
    club_id = request.query_params.get("id", "").strip()
    if not club_url and not club_id:
        return Response({"detail": "Provide ?url= or ?id= to lookup a club."}, status=status.HTTP_400_BAD_REQUEST)

    client = build_campfire_client()
    try:
        club_data = client.resolve_club(club_url) if club_url else client.get_club(club_id)
    except CampfireError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    club = persist_club(club_data)
    club = CampfireClub.objects.select_related("creator").get(pk=club.pk)
    serializer = CampfireClubSerializer(club, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)
