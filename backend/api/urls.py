from django.urls import path

from .views import campfire_config, campfire_import_event, campfire_lookup_club, health

urlpatterns = [
    path("health/", health, name="health"),
    path("campfire/config/", campfire_config, name="campfire-config"),
    path("campfire/events/import/", campfire_import_event, name="campfire-import-event"),
    path("campfire/clubs/lookup/", campfire_lookup_club, name="campfire-club-lookup"),
]
