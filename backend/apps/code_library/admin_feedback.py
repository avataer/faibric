"""
Admin Feedback Interface - LLM-powered admin review system.

Admin answers questions in natural language.
System applies feedback automatically.
"""
import logging
import json
from typing import Dict, List
from django.conf import settings
from django.utils import timezone

from . import constants
from .models import LibraryItem, AdminFeedbackQuestion

logger = logging.getLogger(__name__)


class AdminFeedbackService:
    """
    Handles admin feedback through natural language.
    """
    
    UTILITY_MODEL = constants.UTILITY_MODEL
    
    @classmethod
    def get_pending_questions(cls, limit: int = 10) -> List[Dict]:
        """
        Get pending questions for admin to answer.
        Returns questions in a friendly format.
        """
        questions = AdminFeedbackQuestion.objects.filter(
            answered_at__isnull=True
        ).select_related('library_item').order_by('-created_at')[:limit]
        
        return [
            {
                'id': str(q.id),
                'question': q.question,
                'type': q.question_type,
                'context': q.context,
                'item_name': q.library_item.name,
                'item_id': str(q.library_item.id),
                'created_at': q.created_at.isoformat(),
            }
            for q in questions
        ]
    
    @classmethod
    def get_items_needing_review(cls, limit: int = 20) -> List[Dict]:
        """
        Get library items that need admin review.
        """
        items = LibraryItem.objects.filter(
            needs_review=True,
            is_active=True,
        ).order_by('-created_at')[:limit]
        
        return [
            {
                'id': str(item.id),
                'name': item.name,
                'description': item.description[:200],
                'quality_score': item.quality_score,
                'usage_count': item.usage_count,
                'created_at': item.created_at.isoformat(),
                'pending_questions': item.feedback_questions.filter(answered_at__isnull=True).count(),
            }
            for item in items
        ]
    
    @classmethod
    def answer_question(cls, question_id: str, answer: str) -> Dict:
        """
        Admin answers a question in natural language.
        System interprets and applies the feedback.
        """
        import anthropic
        
        try:
            question = AdminFeedbackQuestion.objects.select_related('library_item').get(id=question_id)
        except AdminFeedbackQuestion.DoesNotExist:
            return {'success': False, 'error': 'Question not found'}
        
        # Store the raw answer
        question.answer = answer
        question.answered_at = timezone.now()
        question.save()
        
        # Use LLM to interpret the answer and determine action
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        interpret_prompt = f"""Interpret this admin feedback and determine what action to take.

Question: "{question.question}"
Question type: {question.question_type}
Admin's answer: "{answer}"

Current item quality score: {question.library_item.quality_score}

Determine the action. Return JSON only:
{{
    "understood": true/false,
    "sentiment": "positive" | "negative" | "neutral",
    "quality_adjustment": -0.2 to +0.2 (how much to adjust quality score),
    "should_deactivate": true/false (if admin explicitly rejects),
    "summary": "one sentence summary of feedback",
    "tags_to_add": ["tag1", "tag2"] or [],
    "improvement_note": "what to improve" or null
}}

Return ONLY valid JSON."""

        try:
            response = client.messages.create(
                model=cls.UTILITY_MODEL,
                max_tokens=500,
                messages=[{"role": "user", "content": interpret_prompt}]
            )
            
            result_text = response.content[0].text.strip()
            if result_text.startswith('```'):
                import re
                result_text = re.sub(r'^```\w*\n?', '', result_text)
                result_text = re.sub(r'\n?```$', '', result_text)
            
            interpretation = json.loads(result_text)
            
            # Apply the feedback
            item = question.library_item
            
            # Adjust quality score
            adjustment = interpretation.get('quality_adjustment', 0)
            item.quality_score = max(0, min(1, item.quality_score + adjustment))
            
            # Deactivate if rejected
            if interpretation.get('should_deactivate'):
                item.is_active = False
                logger.info(f"[Feedback] Deactivated item {item.id} based on admin feedback")
            
            # Add tags
            new_tags = interpretation.get('tags_to_add', [])
            if new_tags:
                item.tags = list(set(item.tags or []) | set(new_tags))
            
            # Mark as reviewed if no more pending questions
            remaining = item.feedback_questions.filter(answered_at__isnull=True).count()
            if remaining == 0:
                item.needs_review = False
            
            item.save()
            
            # Mark question as applied
            question.applied = True
            question.save()
            
            logger.info(f"[Feedback] Applied feedback to {item.id}: {interpretation.get('summary', '')}")
            
            return {
                'success': True,
                'interpretation': interpretation,
                'new_quality_score': item.quality_score,
                'remaining_questions': remaining,
            }
            
        except Exception as e:
            logger.error(f"[Feedback] Failed to interpret answer: {e}")
            return {
                'success': False,
                'error': str(e),
            }
    
    @classmethod
    def quick_feedback(cls, item_id: str, feedback: str) -> Dict:
        """
        Admin gives quick feedback on an item in natural language.
        No predefined questions - just free-form feedback.
        """
        import anthropic
        
        try:
            item = LibraryItem.objects.get(id=item_id)
        except LibraryItem.DoesNotExist:
            return {'success': False, 'error': 'Item not found'}
        
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        interpret_prompt = f"""Interpret this admin feedback about a code component.

Component: "{item.name}"
Current quality score: {item.quality_score}
Current tags: {item.tags}

Admin's feedback: "{feedback}"

Determine what actions to take. Return JSON only:
{{
    "sentiment": "positive" | "negative" | "neutral",
    "quality_adjustment": -0.3 to +0.3,
    "should_deactivate": true/false,
    "tags_to_add": [],
    "tags_to_remove": [],
    "new_keywords": "comma,separated,keywords" or null,
    "summary": "what the admin said"
}}

Examples:
- "This looks great, well structured" → positive, +0.2
- "Too much boilerplate, not reusable" → negative, -0.2
- "Good but needs dark mode" → neutral, +0.05, tags: ["needs-dark-mode"]
- "Delete this, it's broken" → negative, should_deactivate: true

Return ONLY valid JSON."""

        try:
            response = client.messages.create(
                model=cls.UTILITY_MODEL,
                max_tokens=500,
                messages=[{"role": "user", "content": interpret_prompt}]
            )
            
            result_text = response.content[0].text.strip()
            if result_text.startswith('```'):
                import re
                result_text = re.sub(r'^```\w*\n?', '', result_text)
                result_text = re.sub(r'\n?```$', '', result_text)
            
            interpretation = json.loads(result_text)
            
            # Apply changes
            adjustment = interpretation.get('quality_adjustment', 0)
            item.quality_score = max(0, min(1, item.quality_score + adjustment))
            
            if interpretation.get('should_deactivate'):
                item.is_active = False
            
            # Handle tags
            current_tags = set(item.tags or [])
            current_tags |= set(interpretation.get('tags_to_add', []))
            current_tags -= set(interpretation.get('tags_to_remove', []))
            item.tags = list(current_tags)
            
            # Handle keywords
            if interpretation.get('new_keywords'):
                existing = item.keywords.split(', ') if item.keywords else []
                new = interpretation['new_keywords'].split(',')
                item.keywords = ', '.join(set(existing + new))
            
            item.needs_review = False
            item.save()
            
            # Store feedback as answered question for history
            AdminFeedbackQuestion.objects.create(
                library_item=item,
                question="Quick feedback from admin",
                question_type='quality',
                context=feedback[:200],
                answer=feedback,
                answered_at=timezone.now(),
                applied=True,
            )
            
            logger.info(f"[Feedback] Quick feedback applied to {item.id}: {interpretation.get('summary', '')}")
            
            return {
                'success': True,
                'interpretation': interpretation,
                'new_quality_score': item.quality_score,
            }
            
        except Exception as e:
            logger.error(f"[Feedback] Failed to apply quick feedback: {e}")
            return {
                'success': False,
                'error': str(e),
            }


def generate_admin_dashboard_html() -> str:
    """
    Generate HTML for the admin feedback dashboard.
    """
    items = AdminFeedbackService.get_items_needing_review()
    questions = AdminFeedbackService.get_pending_questions()
    
    items_html = ""
    for item in items:
        items_html += f"""
        <div class="item-card">
            <h3>{item['name'][:50]}</h3>
            <p>{item['description']}</p>
            <div class="stats">
                <span>Quality: {item['quality_score']:.0%}</span>
                <span>Used: {item['usage_count']}x</span>
                <span>Questions: {item['pending_questions']}</span>
            </div>
            <form method="post" action="/api/library/feedback/quick/">
                <input type="hidden" name="item_id" value="{item['id']}">
                <input type="text" name="feedback" placeholder="Your feedback in plain English..." style="width:100%;padding:8px;">
                <button type="submit">Submit Feedback</button>
            </form>
        </div>
        """
    
    questions_html = ""
    for q in questions:
        questions_html += f"""
        <div class="question-card">
            <p class="context">Re: {q['item_name']}</p>
            <p class="question">{q['question']}</p>
            <form method="post" action="/api/library/feedback/answer/">
                <input type="hidden" name="question_id" value="{q['id']}">
                <input type="text" name="answer" placeholder="Your answer..." style="width:100%;padding:8px;">
                <button type="submit">Answer</button>
            </form>
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Feedback - Faibric</title>
        <style>
            * {{ font-family: -apple-system, sans-serif; margin:0; padding:0; box-sizing:border-box; }}
            body {{ background:#0a0a1a; color:#e2e8f0; padding:40px; }}
            h1 {{ margin-bottom:30px; }}
            h2 {{ margin:30px 0 15px; color:#94a3b8; }}
            .grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(400px, 1fr)); gap:20px; }}
            .item-card, .question-card {{ background:#1e293b; padding:20px; border-radius:12px; }}
            .item-card h3 {{ margin-bottom:10px; }}
            .stats {{ display:flex; gap:15px; margin:15px 0; font-size:13px; color:#64748b; }}
            .context {{ font-size:12px; color:#64748b; margin-bottom:8px; }}
            .question {{ font-weight:500; margin-bottom:15px; }}
            input[type="text"] {{ background:#0f172a; border:1px solid #334155; border-radius:8px; color:white; margin-bottom:10px; }}
            button {{ background:#3b82f6; color:white; border:none; padding:8px 16px; border-radius:8px; cursor:pointer; }}
            button:hover {{ background:#2563eb; }}
            .back {{ color:#94a3b8; text-decoration:none; }}
        </style>
    </head>
    <body>
        <a href="/api/analytics/dashboard/" class="back">← Back to Dashboard</a>
        <h1>Admin Feedback</h1>
        
        <h2>Pending Questions ({len(questions)})</h2>
        <div class="grid">
            {questions_html or '<p style="color:#64748b">No pending questions</p>'}
        </div>
        
        <h2>Items Needing Review ({len(items)})</h2>
        <div class="grid">
            {items_html or '<p style="color:#64748b">All items reviewed</p>'}
        </div>
    </body>
    </html>
    """
