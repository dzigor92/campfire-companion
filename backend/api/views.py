from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def health(_request):
    """Simple health check endpoint the frontend can call."""
    return Response({"status": "ok"})
