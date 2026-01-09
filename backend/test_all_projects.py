#!/usr/bin/env python
"""
Test Faibric by building all 19 Lovable-style use cases as a customer.

This script:
1. Creates a session for each project type
2. Submits the prompt
3. Triggers the build
4. Deploys to Render
5. Reports results
"""

import os
import sys
import django
import time
import secrets

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'faibric_backend.settings')
django.setup()

from apps.onboarding.models import LandingSession
from apps.projects.models import Project
from apps.onboarding.build_service import BuildService
from apps.deployment.render_deployer import RenderDeployer
from django.contrib.auth import get_user_model

User = get_user_model()

# All 19 project types with customer-like prompts
PROJECTS_TO_BUILD = [
    # Dashboard use-cases (7)
    {
        "name": "Ad Campaign Dashboard",
        "prompt": "Build an ad campaign analytics dashboard showing campaign performance metrics, spend vs ROI charts, click-through rates, and conversion tracking. Include filters for date range and campaign selection."
    },
    {
        "name": "AI Business Insights Dashboard",
        "prompt": "Create an AI-powered business insights dashboard with key metrics, trend analysis charts, predictive indicators, and automated recommendations. Show revenue, growth, and customer metrics."
    },
    {
        "name": "Customer Support Dashboard",
        "prompt": "Build a customer support dashboard showing ticket volume, response times, satisfaction scores, and agent performance. Include a ticket list with status indicators."
    },
    {
        "name": "Data Visualization Dashboard",
        "prompt": "Create a data visualization dashboard with multiple chart types - line charts, bar charts, and pie charts. Include interactive filters and a clean, modern design."
    },
    {
        "name": "IT Infrastructure Dashboard",
        "prompt": "Build an IT infrastructure monitoring dashboard showing server status, CPU/memory usage, network traffic, and system alerts. Include status indicators for each service."
    },
    {
        "name": "Manufacturing Dashboard",
        "prompt": "Create a manufacturing production dashboard with production line status, output metrics, quality indicators, and downtime tracking. Include real-time production stats."
    },
    {
        "name": "Event Analytics Dashboard",
        "prompt": "Build a virtual event analytics dashboard showing attendance, engagement metrics, session popularity, and attendee demographics with charts and KPIs."
    },
    # Full-Stack App use-cases (4)
    {
        "name": "CRM System",
        "prompt": "Build a CRM system with contact management, deal pipeline view, activity feed, and contact cards. Include a kanban-style pipeline for sales stages."
    },
    {
        "name": "Event Management Platform",
        "prompt": "Create an event management platform with event listings, calendar view, ticket selection, and attendee management. Include event cards and registration forms."
    },
    {
        "name": "Project Management Tool",
        "prompt": "Build a project management tool with kanban board, task cards, team member avatars, and due date tracking. Include task creation and status management."
    },
    {
        "name": "Survey Builder",
        "prompt": "Create a survey builder application with question types (multiple choice, rating, text), a survey preview, and response visualization charts."
    },
    # Internal Tools use-cases (8)
    {
        "name": "Forecasting Tool",
        "prompt": "Build an AI-powered forecasting and budgeting tool with budget allocation, forecast charts, variance analysis, and scenario planning features."
    },
    {
        "name": "Compliance Tracker",
        "prompt": "Create a compliance tracking software with requirements checklist, status indicators, progress bars, and audit trail. Include filtering by category."
    },
    {
        "name": "Expense Management",
        "prompt": "Build an expense management tool with expense submission form, approval workflow, spending analytics charts, and category breakdown."
    },
    {
        "name": "Team Communication",
        "prompt": "Create an internal communication platform with message feed, team channels, notification badges, and user presence indicators."
    },
    {
        "name": "Market Research Tool",
        "prompt": "Build a market research tool with survey results display, competitor analysis cards, trend charts, and data export functionality."
    },
    {
        "name": "Internal Project Tracker",
        "prompt": "Create an internal project management tool with project cards, timeline view, resource allocation, and milestone tracking with progress indicators."
    },
    {
        "name": "Remote Workforce Tools",
        "prompt": "Build a remote workforce management tool with team availability calendar, task assignments, time tracking, and productivity metrics dashboard."
    },
    {
        "name": "Revenue Dashboard",
        "prompt": "Create a revenue and cash flow dashboard with income/expense tracking, cash flow charts, invoice status, and financial KPI metrics."
    },
]


def get_or_create_test_user():
    """Get or create a test user for building projects."""
    user, created = User.objects.get_or_create(
        username='faibric_test',
        defaults={
            'email': 'test@faibric.ai',
            'is_active': True
        }
    )
    return user


def create_session_and_project(project_spec):
    """Create a session and project for a customer request."""
    
    # Create session token
    session_token = secrets.token_urlsafe(32)
    
    # Create session
    session = LandingSession.objects.create(
        session_token=session_token,
        initial_request=project_spec["prompt"],
        status='building',
        email='test@faibric.ai',
        email_verified=True
    )
    
    # Get test user
    user = get_or_create_test_user()
    
    # Create project
    project = Project.objects.create(
        user=user,
        name=project_spec["name"],
        description=project_spec["prompt"],
        user_prompt=project_spec["prompt"],
        status='building'
    )
    
    # Link session to project
    session.converted_to_project = project
    session.save()
    
    return session, project


def build_and_deploy(session, project):
    """Build the app and deploy to Render."""
    
    print(f"  Building app...")
    
    try:
        # Use the BuildService.build_from_session
        BuildService.build_from_session(session.session_token)
        
        # Refresh the project from DB
        project.refresh_from_db()
        
        if project.status == 'deployed' and project.deployment_url:
            return project.deployment_url, None
        else:
            return None, f"Build finished but status={project.status}, url={project.deployment_url}"
            
    except Exception as e:
        import traceback
        return None, f"{e}\n{traceback.format_exc()}"


def main():
    """Test all 19 project types."""
    print("=" * 70)
    print("TESTING ALL 19 LOVABLE-STYLE USE CASES")
    print("=" * 70)
    
    results = []
    
    for i, spec in enumerate(PROJECTS_TO_BUILD):
        print(f"\n[{i+1}/19] {spec['name']}")
        print(f"  Prompt: {spec['prompt'][:60]}...")
        
        try:
            # Create session and project
            session, project = create_session_and_project(spec)
            print(f"  Session ID: {session.id}, Project ID: {project.id}")
            
            # Build and deploy
            url, error = build_and_deploy(session, project)
            
            if url:
                print(f"  ✓ SUCCESS: {url}")
                results.append({
                    "name": spec["name"],
                    "prompt": spec["prompt"],
                    "url": url,
                    "status": "success"
                })
            else:
                print(f"  ✗ FAILED: {error}")
                results.append({
                    "name": spec["name"],
                    "prompt": spec["prompt"],
                    "error": error,
                    "status": "failed"
                })
                
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            results.append({
                "name": spec["name"],
                "prompt": spec["prompt"],
                "error": str(e),
                "status": "error"
            })
        
        # Small delay between projects to avoid rate limits
        time.sleep(2)
    
    # Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    
    success = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] != "success"]
    
    print(f"\nSuccessful: {len(success)}/19")
    print(f"Failed: {len(failed)}/19")
    
    if success:
        print("\n--- SUCCESSFUL PROJECTS ---")
        for r in success:
            print(f"✓ {r['name']}")
            print(f"  URL: {r['url']}")
            print(f"  Prompt: {r['prompt'][:80]}...")
            print()
    
    if failed:
        print("\n--- FAILED PROJECTS ---")
        for r in failed:
            print(f"✗ {r['name']}: {r.get('error', 'Unknown error')}")
    
    # Return success rate
    return len(success), len(failed)


if __name__ == '__main__':
    success, failed = main()
    print(f"\n{'='*70}")
    print(f"FINAL: {success} successful, {failed} failed")
    print(f"{'='*70}")

