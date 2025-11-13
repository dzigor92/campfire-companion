from django.urls import path

from .views import (
    campfire_config,
    campfire_import_club_history,
    campfire_import_event,
    campfire_lookup_club,
    campfire_tokens,
    health,
    login_user,
    logout_user,
    link_campfire_account,
    register_user,
)

urlpatterns = [
    path("health/", health, name="health"),
    path("auth/register/", register_user, name="auth-register"),
    path("auth/login/", login_user, name="auth-login"),
    path("auth/logout/", logout_user, name="auth-logout"),
    path("auth/campfire/", link_campfire_account, name="auth-link-campfire"),
    path("campfire/config/", campfire_config, name="campfire-config"),
    path("campfire/events/import/", campfire_import_event, name="campfire-import-event"),
    path("campfire/clubs/import-history/", campfire_import_club_history, name="campfire-import-club-history"),
    path("campfire/clubs/lookup/", campfire_lookup_club, name="campfire-club-lookup"),
    path("campfire/tokens/", campfire_tokens, name="campfire-tokens"),
]
