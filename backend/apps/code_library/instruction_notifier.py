"""
INSTRUCTION SOLUTION NOTIFIER
=============================

Sends notifications when instruction-based solutions are detected.

Notification channels:
1. Email (if configured)
2. Webhook (Slack, Discord, etc.)
3. Console log (always)
4. Database alert (always)
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class InstructionNotifier:
    """
    Sends notifications when instruction-based solutions are detected.
    """
    
    def __init__(self):
        # Get notification settings from environment
        self.email_to = os.environ.get('INSTRUCTION_ALERT_EMAIL', '')
        self.webhook_url = os.environ.get('INSTRUCTION_ALERT_WEBHOOK', '')
        self.slack_webhook = os.environ.get('SLACK_WEBHOOK_URL', '')
    
    def notify(
        self,
        entry_id: str,
        file_path: str,
        line_number: int,
        instruction_text: str,
        missing_enforcement: str
    ):
        """
        Send notification about a new instruction-based solution.
        """
        message = self._format_message(
            entry_id, file_path, line_number, 
            instruction_text, missing_enforcement
        )
        
        # Always log to console
        self._log_to_console(message)
        
        # Always save to database alerts
        self._save_alert(entry_id, message)
        
        # Send to webhook if configured
        if self.webhook_url or self.slack_webhook:
            self._send_webhook(message, entry_id)
        
        # Send email if configured
        if self.email_to:
            self._send_email(message, entry_id)
    
    def _format_message(
        self,
        entry_id: str,
        file_path: str,
        line_number: int,
        instruction_text: str,
        missing_enforcement: str
    ) -> str:
        return f"""
[INSTRUCTION-BASED SOLUTION DETECTED]

ID: {entry_id}
File: {file_path}:{line_number}
Time: {datetime.now().isoformat()}

Instruction:
{instruction_text}

Missing Enforcement:
{missing_enforcement}

Action Required:
Convert this instruction to code enforcement.
See: /api/library/instruction-log/

---
This is an automated alert from Faibric.
"""
    
    def _log_to_console(self, message: str):
        """Log prominently to console."""
        border = "=" * 60
        logger.warning(f"\n{border}\n{message}\n{border}")
    
    def _save_alert(self, entry_id: str, message: str):
        """Save alert to database for dashboard display."""
        try:
            from .models import Alert
            Alert.objects.create(
                alert_type='instruction_solution',
                title=f'Instruction-based solution detected: {entry_id}',
                message=message,
                severity='warning',
                is_read=False
            )
        except Exception:
            pass  # Alert model might not exist
    
    def _send_webhook(self, message: str, entry_id: str):
        """Send to webhook (Slack, Discord, etc.)."""
        webhook_url = self.slack_webhook or self.webhook_url
        
        if not webhook_url:
            return
        
        try:
            # Slack-compatible format
            payload = {
                "text": f"[ALERT] Instruction-based solution detected: {entry_id}",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Instruction-based solution detected*\n```{message[:500]}```"
                        }
                    }
                ]
            }
            
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"[NOTIFIER] Webhook sent for {entry_id}")
            else:
                logger.warning(f"[NOTIFIER] Webhook failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"[NOTIFIER] Webhook error: {e}")
    
    def _send_email(self, message: str, entry_id: str):
        """Send email notification."""
        if not self.email_to:
            return
        
        try:
            from django.core.mail import send_mail
            
            send_mail(
                subject=f'[Faibric Alert] Instruction-based solution: {entry_id}',
                message=message,
                from_email='alerts@faibric.app',
                recipient_list=[self.email_to],
                fail_silently=True
            )
            logger.info(f"[NOTIFIER] Email sent to {self.email_to}")
            
        except Exception as e:
            logger.error(f"[NOTIFIER] Email error: {e}")


# Global instance
_notifier = None


def get_notifier() -> InstructionNotifier:
    """Get the global notifier."""
    global _notifier
    if _notifier is None:
        _notifier = InstructionNotifier()
    return _notifier


def notify_instruction_solution(
    entry_id: str,
    file_path: str,
    line_number: int,
    instruction_text: str,
    missing_enforcement: str
):
    """Send notification about instruction-based solution."""
    get_notifier().notify(
        entry_id, file_path, line_number,
        instruction_text, missing_enforcement
    )



