from datetime import timedelta

from django.db import models
from django.utils import timezone


class CampfireTokenQuerySet(models.QuerySet):
    def valid(self):
        """Return tokens that remain valid for at least another minute."""
        buffer = timezone.now() + timedelta(minutes=1)
        return self.filter(expires_at__gt=buffer).order_by("expires_at")


class CampfireToken(models.Model):
    """Stores Campfire JWTs so authenticated calls can re-use them."""

    token = models.TextField(unique=True)
    email = models.EmailField(blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CampfireTokenQuerySet.as_manager()

    class Meta:
        ordering = ("expires_at",)

    def __str__(self) -> str:
        return f"{self.email or 'unknown'} ({self.expires_at:%Y-%m-%d %H:%M})"


class CampfireMember(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    username = models.CharField(max_length=150, blank=True)
    display_name = models.CharField(max_length=150, blank=True)
    avatar_url = models.URLField(blank=True)
    club_rank = models.IntegerField(null=True, blank=True)
    raw = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return self.display_name or self.username or self.id


class CampfireClub(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    name = models.CharField(max_length=255)
    avatar_url = models.URLField(blank=True)
    game = models.CharField(max_length=64, blank=True)
    visibility = models.CharField(max_length=64, blank=True)
    created_by_community_ambassador = models.BooleanField(default=False)
    badge_grants = models.JSONField(default=list, blank=True)
    creator = models.ForeignKey(
        CampfireMember,
        related_name="clubs_created",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    raw = models.JSONField(default=dict, blank=True)
    imported_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class CampfireEvent(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    name = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    address = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    cover_photo_url = models.URLField(blank=True)
    map_preview_url = models.URLField(blank=True)
    event_time = models.DateTimeField()
    event_end_time = models.DateTimeField(null=True, blank=True)
    rsvp_status = models.CharField(max_length=32, blank=True)
    created_by_community_ambassador = models.BooleanField(default=False)
    discord_interested = models.IntegerField(default=0)
    badge_grants = models.JSONField(default=list, blank=True)
    campfire_live_event_id = models.CharField(max_length=64, blank=True)
    campfire_live_event_name = models.CharField(max_length=255, blank=True)
    checked_in_members_count = models.IntegerField(default=0)
    members_total = models.IntegerField(default=0)
    club = models.ForeignKey(CampfireClub, related_name="events", on_delete=models.CASCADE)
    creator = models.ForeignKey(CampfireMember, related_name="events_created", on_delete=models.SET_NULL, null=True)
    raw = models.JSONField(default=dict, blank=True)
    imported_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class CampfireEventRSVP(models.Model):
    event = models.ForeignKey(CampfireEvent, related_name="rsvps", on_delete=models.CASCADE)
    member = models.ForeignKey(CampfireMember, related_name="rsvps", on_delete=models.CASCADE)
    status = models.CharField(max_length=32)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("event", "member")
