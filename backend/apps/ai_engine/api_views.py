from rest_framework.views import APIView
from rest_framework.response import Response
from .models_config import get_available_models

class AvailableModelsView(APIView):
    def get(self, request):
        models = get_available_models()
        return Response({"models": models})
