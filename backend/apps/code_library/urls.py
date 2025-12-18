"""
URL patterns for code library API.
"""
from django.urls import path, include
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter
import json

from .views import (
    LibraryCategoryViewSet,
    LibraryItemViewSet,
    ConstraintViewSet,
    CodeGenerationViewSet,
    LibraryStatsView,
)
from .admin_feedback import AdminFeedbackService, generate_admin_dashboard_html

router = DefaultRouter()
router.register(r'categories', LibraryCategoryViewSet, basename='library-categories')
router.register(r'items', LibraryItemViewSet, basename='library-items')
router.register(r'constraints', ConstraintViewSet, basename='constraints')
router.register(r'generate', CodeGenerationViewSet, basename='code-generation')
router.register(r'admin/stats', LibraryStatsView, basename='library-stats')


def feedback_dashboard(request):
    """Admin feedback dashboard."""
    return HttpResponse(generate_admin_dashboard_html(), content_type='text/html')


@csrf_exempt
def quick_feedback(request):
    """Submit quick feedback on an item."""
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)
    
    item_id = request.POST.get('item_id')
    feedback = request.POST.get('feedback')
    
    if not item_id or not feedback:
        return HttpResponse('Missing item_id or feedback', status=400)
    
    result = AdminFeedbackService.quick_feedback(item_id, feedback)
    
    if result.get('success'):
        return HttpResponseRedirect('/api/library/feedback/')
    else:
        return HttpResponse(f"Error: {result.get('error')}", status=400)


@csrf_exempt
def answer_question(request):
    """Answer a pending question."""
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)
    
    question_id = request.POST.get('question_id')
    answer = request.POST.get('answer')
    
    if not question_id or not answer:
        return HttpResponse('Missing question_id or answer', status=400)
    
    result = AdminFeedbackService.answer_question(question_id, answer)
    
    if result.get('success'):
        return HttpResponseRedirect('/api/library/feedback/')
    else:
        return HttpResponse(f"Error: {result.get('error')}", status=400)


def feedback_api(request):
    """Get pending questions and items as JSON."""
    data = {
        'pending_questions': AdminFeedbackService.get_pending_questions(),
        'items_needing_review': AdminFeedbackService.get_items_needing_review(),
    }
    return HttpResponse(json.dumps(data, indent=2), content_type='application/json')


urlpatterns = [
    path('', include(router.urls)),
    # Admin feedback interface
    path('feedback/', feedback_dashboard, name='library-feedback'),
    path('feedback/api/', feedback_api, name='library-feedback-api'),
    path('feedback/quick/', quick_feedback, name='library-quick-feedback'),
    path('feedback/answer/', answer_question, name='library-answer-question'),
]









