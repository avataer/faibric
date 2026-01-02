"""
AI Image Generation Service for Faibric websites.
Uses OpenAI GPT-Image-1.5 to generate images.
Images are uploaded to GitHub and served as static assets on Render.
"""
import os
import re
import logging
import requests
from typing import List, Dict, Tuple, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class ImageGenerator:
    """
    Generates images for websites using OpenAI GPT-Image-1.5.
    Downloads images for upload to GitHub repo.
    """
    
    def __init__(self):
        self.openai_api_key = os.environ.get('OPENAI_API_KEY', '') or getattr(settings, 'OPENAI_API_KEY', '')
        self.use_ai = bool(self.openai_api_key)
        # Store generated images for later upload to GitHub
        self.generated_images: Dict[str, bytes] = {}
        
        if self.use_ai:
            logger.info("[ImageGen] Using OpenAI GPT-Image-1.5 for image generation")
        else:
            logger.warning("[ImageGen] No OpenAI API key - images will not be generated!")
    
    def generate_image(self, prompt: str, width: int = 800, height: int = 600, filename: str = None) -> Tuple[str, bytes]:
        """
        Generate an image from a text prompt.
        Returns tuple of (filename, image_bytes).
        """
        if not self.use_ai:
            raise Exception("OpenAI API key required for image generation")
        
        return self._generate_with_openai(prompt, width, height, filename)
    
    def _generate_with_openai(self, prompt: str, width: int, height: int, filename: str = None) -> Tuple[str, bytes]:
        """
        Generate image using OpenAI GPT-Image-1.5 ONLY.
        Uses low quality for fast generation as per OpenAI cookbook recommendations.
        Downloads and returns (filename, image_bytes) for upload to GitHub.
        
        Based on: https://cookbook.openai.com/examples/multimodal/image-gen-1.5-prompting_guide
        """
        import openai
        
        client = openai.OpenAI(api_key=self.openai_api_key)
        
        # Build structured prompt following OpenAI cookbook best practices:
        # Structure: background/scene -> subject -> key details -> constraints
        enhanced_prompt = self._build_structured_prompt(prompt)
        
        # GPT-Image-1.5 supported sizes: 1024x1024, 1024x1536, 1536x1024, auto
        if width > height * 1.3:
            size = "1536x1024"  # Landscape
        elif height > width * 1.3:
            size = "1024x1536"  # Portrait
        else:
            size = "1024x1024"  # Square
        
        # Generate filename if not provided
        if not filename:
            clean_name = re.sub(r'[^a-z0-9]+', '-', prompt.lower())[:30].strip('-')
            filename = f"{clean_name}.jpg"
        
        try:
            # Use ONLY gpt-image-1.5, quality="low" for fast generation
            response = client.images.generate(
                model="gpt-image-1.5",
                prompt=enhanced_prompt[:1000],
                size=size,
                quality="low",  # Fast generation, still good quality per OpenAI docs
                n=1,
            )
            
            image_url = response.data[0].url
            logger.info(f"[ImageGen] Generated gpt-image-1.5 image: {prompt[:50]}...")
            
            # Download the image
            image_bytes = self._download_image(image_url)
            
            # Store for later upload
            self.generated_images[filename] = image_bytes
            
            return (filename, image_bytes)
            
        except Exception as e:
            # NO FALLBACK - GPT-Image-1.5 is required
            logger.error(f"[ImageGen] GPT-Image-1.5 FAILED: {e}")
            raise Exception(f"GPT-Image-1.5 generation failed. No fallback models allowed.")
    
    def _build_structured_prompt(self, user_prompt: str) -> str:
        """
        Build a structured prompt following OpenAI cookbook best practices.
        Structure: background/scene -> subject -> key details -> constraints
        """
        return f"""Professional website photograph.

Scene: Clean, modern setting appropriate for a business website.

Subject: {user_prompt}

Style: Photorealistic, natural lighting, 35mm lens feel, shallow depth of field.

Constraints:
- No watermarks, no logos, no text overlay
- No artificial or overly stylized effects
- Natural color balance, not oversaturated
- Clean composition with clear focal point
"""
    
    def _download_image(self, image_url: str) -> bytes:
        """Download image from URL and return bytes."""
        try:
            response = requests.get(image_url, timeout=60)
            response.raise_for_status()
            
            logger.info(f"[ImageGen] Downloaded image ({len(response.content)} bytes)")
            return response.content
            
        except Exception as e:
            logger.error(f"[ImageGen] Failed to download image: {e}")
            raise
    
    def get_all_images(self) -> Dict[str, bytes]:
        """Get all generated images for upload to GitHub."""
        return self.generated_images
    
    def clear_images(self):
        """Clear stored images after upload."""
        self.generated_images = {}
    
    def extract_image_descriptions(self, user_request: str) -> List[str]:
        """
        Extract image descriptions from user request.
        Returns list of prompts for image generation.
        """
        descriptions = []
        
        # Extract key themes from the request
        keywords = user_request.lower()
        
        # Common website sections that need images
        if 'hero' in keywords or 'landing' in keywords or 'home' in keywords:
            descriptions.append(f"Hero banner image for {user_request[:50]}")
        
        if 'about' in keywords or 'team' in keywords:
            descriptions.append("Professional team or office environment")
        
        if 'portfolio' in keywords or 'gallery' in keywords:
            descriptions.append(f"Portfolio showcase image for {user_request[:50]}")
        
        if 'service' in keywords or 'product' in keywords:
            descriptions.append(f"Professional service or product image for {user_request[:50]}")
        
        if 'testimonial' in keywords or 'review' in keywords:
            descriptions.append("Professional headshot for testimonial")
        
        # If no specific sections found, generate based on the business type
        if not descriptions:
            descriptions.append(f"Professional website image for {user_request[:100]}")
        
        return descriptions
    
    def generate_images_for_website(self, user_request: str, count: int = 5) -> List[Dict[str, str]]:
        """
        Generate multiple images for a website based on user request.
        Returns list of {prompt, url} dicts.
        """
        descriptions = self.extract_image_descriptions(user_request)
        
        # Pad with generic images if needed
        while len(descriptions) < count:
            idx = len(descriptions) + 1
            descriptions.append(f"Professional image {idx} for {user_request[:50]}")
        
        images = []
        for i, desc in enumerate(descriptions[:count]):
            url = self.generate_image(desc)
            images.append({
                'prompt': desc,
                'url': url,
                'variable': f'image{i + 1}',
            })
        
        return images
    
    def inject_images_into_code(self, code: str, user_request: str) -> Tuple[str, Dict[str, bytes]]:
        """
        Replace placeholder image URLs in generated code with local image paths.
        Generates 1-2 images with GPT-Image-1.5 (quality=low for speed).
        
        Based on OpenAI cookbook: https://cookbook.openai.com/examples/multimodal/image-gen-1.5-prompting_guide
        
        Returns:
            Tuple of (updated_code, dict of {filename: image_bytes})
        """
        if not self.use_ai:
            raise Exception("OpenAI API key required - cannot generate images without it")
        
        # Clear any previous images
        self.clear_images()
        
        # Find all placeholder URLs in the code (picsum pattern with descriptive seeds)
        placeholder_pattern = r'https://picsum\.photos/seed/([^/]+)/(\d+)/(\d+)'
        matches = re.findall(placeholder_pattern, code)
        
        if not matches:
            logger.info("[ImageGen] No placeholder images found in code")
            return code, {}
        
        logger.info(f"[ImageGen] Found {len(matches)} placeholders, generating max 2 images")
        
        # Track processed placeholders to avoid duplicates
        processed = set()
        image_counter = 0
        
        # LIMIT TO 2 IMAGES MAX - per user requirement
        # Prioritize hero/banner images first
        priority_keywords = ['hero', 'banner', 'header', 'main', 'about']
        sorted_matches = sorted(matches, key=lambda m: (
            0 if any(kw in m[0].lower() for kw in priority_keywords) else 1
        ))
        
        for seed, width, height in sorted_matches:
            # STOP after 2 images
            if image_counter >= 2:
                break
                
            # Create unique key for this placeholder
            key = f"{seed}/{width}/{height}"
            
            if key in processed:
                continue
            processed.add(key)
            
            # Build context-aware prompt based on the seed and user request
            prompt = self._build_image_prompt(seed, user_request)
            
            # Create filename from seed
            clean_seed = re.sub(r'[^a-z0-9]+', '-', seed.lower())[:20].strip('-')
            filename = f"{clean_seed}.jpg"
            
            try:
                image_counter += 1
                logger.info(f"[ImageGen] Generating image {image_counter}/2: {seed}")
                
                returned_filename, image_bytes = self.generate_image(prompt, int(width), int(height), filename)
                
                # Replace placeholder URL with local path
                old_url = f'https://picsum.photos/seed/{seed}/{width}/{height}'
                new_url = f'/images/{returned_filename}'
                code = code.replace(old_url, new_url)
                
                logger.info(f"[ImageGen] Generated: {returned_filename}")
                
            except Exception as e:
                # GPT-Image-1.5 failed - this is an error, no fallback
                logger.error(f"[ImageGen] GPT-Image-1.5 FAILED for '{seed}': {e}")
                raise Exception(f"Image generation failed: GPT-Image-1.5 is required but unavailable")
        
        return code, self.get_all_images()
    
    def _build_image_prompt(self, seed: str, user_request: str) -> str:
        """
        Build a structured prompt following OpenAI GPT-Image-1.5 cookbook best practices.
        
        Structure: background/scene -> subject -> key details -> constraints
        Reference: https://cookbook.openai.com/examples/multimodal/image-gen-1.5-prompting_guide
        """
        clean_seed = seed.replace('-', ' ').replace('_', ' ')
        context = user_request[:100]
        
        # Hero/Banner images - wide, impactful
        if any(word in clean_seed.lower() for word in ['hero', 'banner', 'header', 'main']):
            return f"""Professional hero image for a {context} website.

Scene: Wide establishing shot, modern environment relevant to {context}.
Subject: Visual representation of the business/service.
Style: Photorealistic, 35mm wide-angle lens, natural lighting, shallow depth of field.
Mood: Professional, inviting, trustworthy.

Constraints: No text, no watermarks, no logos. Clean composition."""

        # Portrait/Team images
        if any(word in clean_seed.lower() for word in ['portrait', 'team', 'person', 'founder']):
            return f"""Professional business portrait photograph.

Scene: Clean, neutral studio background with soft lighting.
Subject: Professional headshot appropriate for {context}.
Style: Medium close-up, 85mm portrait lens feel, soft natural window light.
Mood: Approachable, confident, professional.

Constraints: No text, no watermarks. Natural skin texture, not over-retouched."""

        # Service/Product images
        if any(word in clean_seed.lower() for word in ['service', 'product', 'work', 'portfolio']):
            return f"""Professional service/product image for {context}.

Scene: Clean, contextual setting showing the service in action.
Subject: {clean_seed} - representing what the business offers.
Style: Photorealistic, natural lighting, clear focal point.
Mood: Professional, high-quality, trustworthy.

Constraints: No text, no watermarks, no logos."""

        # About/Story images
        if any(word in clean_seed.lower() for word in ['about', 'story', 'mission', 'workspace']):
            return f"""Professional "about us" image for {context}.

Scene: Authentic workspace or environment related to the business.
Subject: Behind-the-scenes look at the business/service.
Style: Candid photojournalistic feel, natural light, 35mm lens.
Mood: Authentic, warm, relatable.

Constraints: No text, no watermarks. Should feel real, not staged."""

        # Default - general professional image
        return f"""Professional website photograph for {context}.

Scene: Modern, clean setting appropriate for the business.
Subject: {clean_seed} - relevant to the website's purpose.
Style: Photorealistic, natural lighting, clean composition.
Mood: Professional, modern, trustworthy.

Constraints: No text, no watermarks, no logos, no artificial effects."""


# Singleton instance
_image_generator = None

def get_image_generator() -> ImageGenerator:
    """Get or create the image generator singleton."""
    global _image_generator
    if _image_generator is None:
        _image_generator = ImageGenerator()
    return _image_generator




