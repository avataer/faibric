"""
API views for external service status and testing.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from .services import (
    get_service_status,
    LLMService,
    StripeService,
    GoogleAdsService,
    EmailService,
    SerpAPIService,
)


class ServiceStatusView(APIView):
    """
    Check status of all external services.
    Shows which are in mock mode vs live.
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        status = get_service_status()
        
        mock_count = sum(1 for s in status.values() if s["mock"])
        live_count = len(status) - mock_count
        
        return Response({
            "summary": {
                "total_services": len(status),
                "mock_mode": mock_count,
                "live_mode": live_count,
            },
            "services": status,
        })


class TestServicesView(APIView):
    """
    Test external services (uses mock if keys not set).
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def post(self, request):
        service = request.data.get("service")
        results = {}
        
        if service == "llm" or service == "all":
            # Test LLM
            result = LLMService.generate_code(
                "Create a simple React component that displays 'Hello World'"
            )
            results["llm"] = {
                "success": True,
                "mock": result.get("mock", False),
                "model": result.get("model"),
                "tokens": result.get("total_tokens"),
                "content_preview": result.get("content", "")[:200] + "...",
            }
        
        if service == "stripe" or service == "all":
            # Test Stripe
            result = StripeService.create_customer("test@example.com", "Test User")
            results["stripe"] = {
                "success": True,
                "mock": result.get("mock", False),
                "customer_id": result.get("id"),
            }
        
        if service == "google_ads" or service == "all":
            # Test Google Ads
            campaigns = GoogleAdsService.get_campaigns()
            results["google_ads"] = {
                "success": True,
                "mock": campaigns[0].get("mock", False) if campaigns else True,
                "campaign_count": len(campaigns),
            }
        
        if service == "email" or service == "all":
            # Test Email (just check status, don't actually send)
            results["email"] = {
                "success": True,
                "mock": EmailService.is_mock_mode(),
                "message": "Mock mode - emails logged to console" if EmailService.is_mock_mode() else "Live mode - emails will be sent",
            }
        
        if service == "serpapi" or service == "all":
            # Test SerpAPI
            result = SerpAPIService.search("test keyword")
            results["serpapi"] = {
                "success": True,
                "mock": result.get("mock", False),
                "results_count": len(result.get("organic_results", [])),
            }
        
        return Response({
            "tested": list(results.keys()),
            "results": results,
        })


class TestLLMView(APIView):
    """
    Test LLM code generation specifically.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        prompt = request.data.get("prompt", "Create a simple todo list component in React")
        
        result = LLMService.generate_code(prompt)
        
        return Response({
            "success": True,
            "mock": result.get("mock", False),
            "model": result.get("model"),
            "input_tokens": result.get("input_tokens"),
            "output_tokens": result.get("output_tokens"),
            "content": result.get("content"),
            "message": result.get("message"),
        })







