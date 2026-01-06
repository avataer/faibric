"""
Faibric Connector V2 - Health Check and Email Notification

Runs tests on every deployment/startup and sends email alerts on failure.
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Alert recipient
ALERT_EMAIL = "gypsum_parley.0j@icloud.com"

# SMTP settings for sending alerts
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "alerts@faibric.com")


def send_alert_email(subject: str, body: str, to_email: str = ALERT_EMAIL) -> bool:
    """
    Send an alert email when Connector V2 tests fail.
    
    Returns True if email was sent successfully.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("[CONNECTOR V2 ALERT] SMTP not configured - logging alert locally")
        logger.critical(f"[CONNECTOR V2 ALERT] Subject: {subject}")
        logger.critical(f"[CONNECTOR V2 ALERT] Body: {body}")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_FROM
        msg['To'] = to_email
        msg['Subject'] = f"🚨 FAIBRIC ALERT: {subject}"
        
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"[CONNECTOR V2] Alert email sent to {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"[CONNECTOR V2] Failed to send alert email: {e}")
        return False


def run_health_check() -> Dict[str, Any]:
    """
    Run Connector V2 health check.
    
    This should be called:
    - On backend startup
    - Before each build
    - Periodically (e.g., every hour)
    
    Returns health status and sends alert if tests fail.
    """
    from .tests import run_tests
    
    logger.info("[CONNECTOR V2] Running health check...")
    
    try:
        report = run_tests()
        
        passed = report['summary']['tests_passed']
        total = report['summary']['tests_total']
        all_passed = report['summary']['all_passed']
        
        status = {
            'healthy': all_passed,
            'tests_passed': passed,
            'tests_total': total,
            'pass_rate': report['summary']['pass_rate'],
            'timestamp': datetime.utcnow().isoformat(),
            'benchmarks': report['benchmarks']
        }
        
        if all_passed:
            logger.info(f"[CONNECTOR V2] Health check PASSED: {passed}/{total} tests")
        else:
            # RED FLAG - Send email alert
            failed_tests = [t for t in report['tests'] if not t['passed']]
            
            alert_body = f"""
CONNECTOR V2 HEALTH CHECK FAILED

Time: {datetime.utcnow().isoformat()}
Tests Passed: {passed}/{total}
Pass Rate: {report['summary']['pass_rate']}

FAILED TESTS:
{chr(10).join(f"- {t['name']}: {t['details']}" for t in failed_tests)}

BENCHMARKS:
{chr(10).join(f"- {b['metric']}: {b['value']}{b['unit']}" for b in report['benchmarks'])}

This is an automated alert from Faibric Connector V2.
The system will continue to use fallback AI-generated wiring until this is fixed.
"""
            
            logger.critical(f"[CONNECTOR V2] Health check FAILED: {passed}/{total} tests")
            send_alert_email(
                subject=f"Connector V2 Tests Failed ({passed}/{total})",
                body=alert_body
            )
            
            status['failed_tests'] = failed_tests
        
        return status
        
    except Exception as e:
        logger.critical(f"[CONNECTOR V2] Health check ERROR: {e}")
        
        send_alert_email(
            subject="Connector V2 Health Check Error",
            body=f"Health check failed with exception:\n\n{str(e)}\n\nTime: {datetime.utcnow().isoformat()}"
        )
        
        return {
            'healthy': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


def is_connector_v2_healthy() -> bool:
    """
    Quick check if Connector V2 is healthy.
    
    Use this before deciding whether to use Connector V2 or fallback to AI.
    """
    try:
        from .tests import run_tests
        report = run_tests()
        return report['summary']['all_passed']
    except Exception:
        return False


# Run health check on module import (startup)
_startup_status = None

def get_startup_status() -> Dict[str, Any]:
    """Get the startup health check status."""
    global _startup_status
    if _startup_status is None:
        _startup_status = run_health_check()
    return _startup_status

