#!/usr/bin/env python3
"""
Faibric Service Monitor
Watches backend and frontend services, sends email alerts on failure,
and attempts auto-restart.
"""
import os
import sys
import time
import subprocess
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

# Configuration
BACKEND_URL = "http://localhost:8000/api/health/"
FRONTEND_URL = "http://localhost:5173/"
CHECK_INTERVAL = 30  # seconds
MAX_RESTART_ATTEMPTS = 3
RESTART_COOLDOWN = 60  # seconds between restart attempts

# Alert configuration
ALERT_EMAIL = os.getenv('ALERT_EMAIL', 'amptiness@icloud.com')
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASS = os.getenv('SMTP_PASS', '')
FROM_EMAIL = os.getenv('FROM_EMAIL', 'monitor@faibric.com')

# Project paths
PROJECT_ROOT = Path(__file__).parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# State tracking
last_alert_time = {}
restart_attempts = {"backend": 0, "frontend": 0}
last_restart_time = {"backend": 0, "frontend": 0}


def log(message: str, level: str = "INFO"):
    """Log with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")
    
    # Also write to log file
    log_file = PROJECT_ROOT / "monitor.log"
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] [{level}] {message}\n")


def send_alert(subject: str, message: str):
    """Send email alert."""
    # Rate limit: max 1 alert per service per 5 minutes
    alert_key = subject
    now = time.time()
    if alert_key in last_alert_time:
        if now - last_alert_time[alert_key] < 300:
            log(f"Alert rate limited: {subject}", "WARN")
            return False
    
    last_alert_time[alert_key] = now
    
    # Try SendGrid first
    sendgrid_key = os.getenv('SENDGRID_API_KEY', '')
    if sendgrid_key and sendgrid_key.startswith('SG.'):
        try:
            import json
            headers = {
                "Authorization": f"Bearer {sendgrid_key}",
                "Content-Type": "application/json"
            }
            data = {
                "personalizations": [{"to": [{"email": ALERT_EMAIL}]}],
                "from": {"email": FROM_EMAIL},
                "subject": f"[FAIBRIC ALERT] {subject}",
                "content": [{"type": "text/plain", "value": message}]
            }
            resp = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers=headers,
                json=data,
                timeout=10
            )
            if resp.status_code in (200, 202):
                log(f"Alert sent via SendGrid to {ALERT_EMAIL}", "INFO")
                return True
        except Exception as e:
            log(f"SendGrid failed: {e}", "ERROR")
    
    # Try SMTP
    if SMTP_USER and SMTP_PASS:
        try:
            msg = MIMEMultipart()
            msg['From'] = FROM_EMAIL
            msg['To'] = ALERT_EMAIL
            msg['Subject'] = f"[FAIBRIC ALERT] {subject}"
            msg.attach(MIMEText(message, 'plain'))
            
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
            
            log(f"Alert sent via SMTP to {ALERT_EMAIL}", "INFO")
            return True
        except Exception as e:
            log(f"SMTP failed: {e}", "ERROR")
    
    # Fallback: macOS notification
    try:
        subprocess.run([
            "osascript", "-e",
            f'display notification "{message}" with title "FAIBRIC ALERT" subtitle "{subject}"'
        ], check=True, capture_output=True)
        log(f"Alert sent via macOS notification", "INFO")
    except:
        pass
    
    # Fallback: terminal bell and file
    print(f"\a\n{'='*60}\n[ALERT] {subject}\n{message}\n{'='*60}\n")
    
    # Write to alert file
    alert_file = PROJECT_ROOT / "ALERTS.txt"
    with open(alert_file, "a") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"[{datetime.now()}] {subject}\n")
        f.write(f"{message}\n")
    
    return False


def check_backend() -> tuple[bool, str]:
    """Check if backend is healthy."""
    try:
        resp = requests.get(BACKEND_URL, timeout=5)
        if resp.status_code == 200:
            return True, "Backend healthy"
        return False, f"Backend returned status {resp.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Backend not responding (connection refused)"
    except requests.exceptions.Timeout:
        return False, "Backend timed out"
    except Exception as e:
        return False, f"Backend error: {e}"


def check_frontend() -> tuple[bool, str]:
    """Check if frontend is healthy."""
    try:
        resp = requests.get(FRONTEND_URL, timeout=5)
        if resp.status_code == 200:
            return True, "Frontend healthy"
        return False, f"Frontend returned status {resp.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Frontend not responding (connection refused)"
    except requests.exceptions.Timeout:
        return False, "Frontend timed out"
    except Exception as e:
        return False, f"Frontend error: {e}"


def restart_backend():
    """Restart backend service."""
    now = time.time()
    if now - last_restart_time["backend"] < RESTART_COOLDOWN:
        log("Backend restart on cooldown", "WARN")
        return False
    
    if restart_attempts["backend"] >= MAX_RESTART_ATTEMPTS:
        log("Max backend restart attempts reached", "ERROR")
        return False
    
    log("Restarting backend...", "WARN")
    
    # Kill existing
    subprocess.run(["pkill", "-9", "-f", "manage.py"], capture_output=True)
    time.sleep(2)
    
    # Start new
    env = os.environ.copy()
    subprocess.Popen(
        ["python", "manage.py", "runserver", "0.0.0.0:8000"],
        cwd=BACKEND_DIR,
        env=env,
        stdout=open("/tmp/django.log", "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True
    )
    
    restart_attempts["backend"] += 1
    last_restart_time["backend"] = now
    
    # Wait and verify
    time.sleep(5)
    ok, msg = check_backend()
    if ok:
        log("Backend restarted successfully", "INFO")
        restart_attempts["backend"] = 0
        return True
    else:
        log(f"Backend restart failed: {msg}", "ERROR")
        return False


def restart_frontend():
    """Restart frontend service."""
    now = time.time()
    if now - last_restart_time["frontend"] < RESTART_COOLDOWN:
        log("Frontend restart on cooldown", "WARN")
        return False
    
    if restart_attempts["frontend"] >= MAX_RESTART_ATTEMPTS:
        log("Max frontend restart attempts reached", "ERROR")
        return False
    
    log("Restarting frontend...", "WARN")
    
    # Kill existing
    subprocess.run(["pkill", "-9", "-f", "vite"], capture_output=True)
    time.sleep(2)
    
    # Start new
    subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND_DIR,
        stdout=open("/tmp/frontend.log", "a"),
        stderr=subprocess.STDOUT,
        start_new_session=True
    )
    
    restart_attempts["frontend"] += 1
    last_restart_time["frontend"] = now
    
    # Wait and verify
    time.sleep(5)
    ok, msg = check_frontend()
    if ok:
        log("Frontend restarted successfully", "INFO")
        restart_attempts["frontend"] = 0
        return True
    else:
        log(f"Frontend restart failed: {msg}", "ERROR")
        return False


def run_monitor():
    """Main monitoring loop."""
    log("Faibric Monitor started", "INFO")
    log(f"Watching: {BACKEND_URL}, {FRONTEND_URL}", "INFO")
    log(f"Check interval: {CHECK_INTERVAL}s", "INFO")
    log(f"Alert email: {ALERT_EMAIL}", "INFO")
    
    backend_was_down = False
    frontend_was_down = False
    
    while True:
        try:
            # Check backend
            backend_ok, backend_msg = check_backend()
            if not backend_ok:
                log(f"Backend DOWN: {backend_msg}", "ERROR")
                
                if not backend_was_down:
                    send_alert(
                        "Backend Service DOWN",
                        f"The Faibric backend is not responding.\n\n"
                        f"Error: {backend_msg}\n"
                        f"Time: {datetime.now()}\n\n"
                        f"Attempting auto-restart..."
                    )
                
                backend_was_down = True
                
                # Try restart
                if restart_backend():
                    send_alert(
                        "Backend Service RECOVERED",
                        f"The Faibric backend has been automatically restarted and is now healthy.\n"
                        f"Time: {datetime.now()}"
                    )
                    backend_was_down = False
            else:
                if backend_was_down:
                    log("Backend recovered", "INFO")
                    send_alert(
                        "Backend Service RECOVERED",
                        f"The Faibric backend is now healthy.\n"
                        f"Time: {datetime.now()}"
                    )
                backend_was_down = False
                restart_attempts["backend"] = 0
            
            # Check frontend
            frontend_ok, frontend_msg = check_frontend()
            if not frontend_ok:
                log(f"Frontend DOWN: {frontend_msg}", "ERROR")
                
                if not frontend_was_down:
                    send_alert(
                        "Frontend Service DOWN",
                        f"The Faibric frontend is not responding.\n\n"
                        f"Error: {frontend_msg}\n"
                        f"Time: {datetime.now()}\n\n"
                        f"Attempting auto-restart..."
                    )
                
                frontend_was_down = True
                
                # Try restart
                if restart_frontend():
                    send_alert(
                        "Frontend Service RECOVERED",
                        f"The Faibric frontend has been automatically restarted and is now healthy.\n"
                        f"Time: {datetime.now()}"
                    )
                    frontend_was_down = False
            else:
                if frontend_was_down:
                    log("Frontend recovered", "INFO")
                    send_alert(
                        "Frontend Service RECOVERED",
                        f"The Faibric frontend is now healthy.\n"
                        f"Time: {datetime.now()}"
                    )
                frontend_was_down = False
                restart_attempts["frontend"] = 0
            
            # Status
            if backend_ok and frontend_ok:
                log("All services healthy", "INFO")
            
        except KeyboardInterrupt:
            log("Monitor stopped by user", "INFO")
            break
        except Exception as e:
            log(f"Monitor error: {e}", "ERROR")
        
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    # Allow setting alert email from command line
    if len(sys.argv) > 1:
        ALERT_EMAIL = sys.argv[1]
    
    run_monitor()
