#!/usr/bin/env python
"""
NFT Artist Customer Test - Tests AI image generation.

Tests the specific prompt: "I am an NFT artist who only draws 7 dogs in the picture.
At least one of dogs is always pink. Make a website for me to attract clients who
want to order my drawings. Add at least one example drawing of seven dogs with
one pink dog on the Gallery page."
"""
import os
import sys
import time
import json
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'faibric_backend.settings')
sys.path.insert(0, '/app')
django.setup()

from apps.onboarding.models import LandingSession, SessionEvent
from apps.onboarding.build_service import BuildService
from apps.projects.models import Project
import secrets
import requests
import logging

# Enable verbose logging for image generation
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_nft_artist_build():
    """Run the NFT artist customer test."""
    prompt = """I am an NFT artist who only draws 7 dogs in the picture. At least one of dogs is always pink. Make a website for me to attract clients who want to order my drawings. Add at least one example drawing of seven dogs with one pink dog on the Gallery page."""

    print("\n" + "="*70)
    print("NFT ARTIST CUSTOMER TEST - AI IMAGE GENERATION")
    print("="*70)
    print(f"Prompt: {prompt}")
    print("="*70)

    # Create session
    session_token = secrets.token_urlsafe(32)
    email = f"test{secrets.token_hex(4)}@faibric.test"

    session = LandingSession.objects.create(
        session_token=session_token,
        initial_request=prompt,
        email=email,
        status='verified'
    )
    print(f"\n[OK] Created session: {session_token[:20]}...")

    # Build the app
    print("\n[BUILDING] Starting build process...")
    start_time = time.time()

    result = BuildService.build_from_session(session_token)

    elapsed = time.time() - start_time
    print(f"\n[TIME] Build time: {elapsed:.1f}s")

    # Analyze result
    if result.get('success'):
        url = result.get('url', '')
        print(f"\n[OK] Build SUCCESS")
        print(f"[URL] {url}")

        # Check session events for image generation logs
        print("\n" + "-"*50)
        print("SESSION EVENTS:")
        print("-"*50)
        events = SessionEvent.objects.filter(session=session).order_by('timestamp')
        for event in events:
            print(f"  - {event.event_type}: {event.event_data.get('message', '')}")

        # Get the project to check generated code
        session.refresh_from_db()
        if session.converted_to_project:
            project = session.converted_to_project
            if project.frontend_code:
                try:
                    code_data = json.loads(project.frontend_code)
                    app_code = code_data.get('App.tsx', '')

                    print("\n" + "-"*50)
                    print("CODE ANALYSIS:")
                    print("-"*50)

                    # Check for picsum placeholders
                    picsum_count = app_code.count('picsum.photos')
                    print(f"  - Picsum placeholders found: {picsum_count}")

                    # Check for AI-generated image paths
                    ai_image_count = app_code.count('/images/')
                    print(f"  - AI image paths found: {ai_image_count}")

                    # Look for image URLs
                    import re
                    image_urls = re.findall(r'(https?://[^\s"\']+\.(jpg|jpeg|png|gif|webp))', app_code)
                    print(f"  - External image URLs: {len(image_urls)}")
                    for img_url in image_urls[:5]:
                        print(f"    - {img_url[0][:80]}")

                    # Check if code mentions dogs/pink
                    has_dog_reference = 'dog' in app_code.lower()
                    has_pink_reference = 'pink' in app_code.lower()
                    print(f"  - References 'dog' in code: {has_dog_reference}")
                    print(f"  - References 'pink' in code: {has_pink_reference}")

                except Exception as e:
                    print(f"  [ERROR] Could not parse frontend code: {e}")

        # Verify the deployed URL
        print("\n" + "-"*50)
        print("DEPLOYED SITE CHECK:")
        print("-"*50)
        time.sleep(3)  # Give deployment a moment
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                html = resp.text

                # Check HTML for image sources
                picsum_in_html = 'picsum.photos' in html
                ai_images_in_html = '/images/' in html

                print(f"  - Site accessible: {resp.status_code}")
                print(f"  - Has picsum placeholders in HTML: {picsum_in_html}")
                print(f"  - Has /images/ paths in HTML: {ai_images_in_html}")

                # Find all image sources
                import re
                img_srcs = re.findall(r'src=["\']([^"\']+)["\']', html)
                print(f"  - Total img src found: {len(img_srcs)}")
                for src in img_srcs[:10]:
                    print(f"    - {src[:80]}")

            else:
                print(f"  [ERROR] Site returned {resp.status_code}")
        except Exception as e:
            print(f"  [ERROR] Could not access URL: {e}")

        return {
            'success': True,
            'url': url,
            'time': elapsed,
            'picsum_count': picsum_count if 'picsum_count' in dir() else 0,
            'ai_image_count': ai_image_count if 'ai_image_count' in dir() else 0
        }
    else:
        print(f"\n[ERROR] Build FAILED: {result.get('error', 'Unknown error')}")
        return {'success': False, 'error': result.get('error')}

if __name__ == '__main__':
    print("\nStarting NFT Artist Customer Test...")
    result = test_nft_artist_build()

    print("\n" + "="*70)
    print("FINAL RESULT:")
    print("="*70)
    print(json.dumps(result, indent=2, default=str))

    sys.exit(0 if result.get('success') else 1)
