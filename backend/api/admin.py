from django.contrib import admin

from .models import (
    CampfireClub,
    CampfireEvent,
    CampfireEventRSVP,
    CampfireMember,
    CampfireToken,
)


@admin.register(CampfireToken)
class CampfireTokenAdmin(admin.ModelAdmin):
    list_display = ("email", "expires_at", "created_at")
    search_fields = ("email",)
    list_filter = ("expires_at",)


@admin.register(CampfireMember)
class CampfireMemberAdmin(admin.ModelAdmin):
    list_display = ("id", "display_name", "username")
    search_fields = ("id", "display_name", "username")


@admin.register(CampfireClub)
class CampfireClubAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "game", "visibility")
    search_fields = ("id", "name")
    autocomplete_fields = ("creator",)


class CampfireEventRSVPInline(admin.TabularInline):
    model = CampfireEventRSVP
    extra = 0
    autocomplete_fields = ("member",)


@admin.register(CampfireEvent)
class CampfireEventAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "event_time", "club", "created_by_community_ambassador")
    search_fields = ("id", "name", "club__name")
    autocomplete_fields = ("club", "creator")
    inlines = [CampfireEventRSVPInline]
