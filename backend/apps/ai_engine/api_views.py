from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models_config import get_available_models

class AvailableModelsView(APIView):
    """List available AI models - public endpoint"""
    permission_classes = [AllowAny]

    def get(self, request):
        models = get_available_models()
        return Response({"models": models, "_deploy_version": "2026-01-27-v3"})
