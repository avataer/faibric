"""
Enhanced code generation pipeline with research and library reuse.
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

from django.conf import settings

from apps.code_library.models import LibraryItem, LibraryVersion
from apps.code_library.search import LibrarySearchService
from apps.code_library.embeddings import embed_code_sync

from .research import ResearchService, research_topic_sync
from .constraints import ConstraintManager, load_constraints_sync
from .prompts import PromptBuilder

logger = logging.getLogger(__name__)


@dataclass
class GenerationRequest:
    """Request for code generation."""
    description: str
    language: str = 'typescript'
    item_type: str = 'component'
    
    # Options
    search_library: bool = True
    do_research: bool = True
    apply_constraints: bool = True
    save_to_library: bool = True
    
    # Context
    tenant_id: str = None
    user_id: str = None
    project_id: str = None
    
    # Additional context
    existing_code: str = None
    file_path: str = None


@dataclass
class GenerationResult:
    """Result of code generation."""
    success: bool
    code: str = ''
    
    # Source info
    from_library: bool = False
    library_item_id: str = None
    
    # Research used
    research_summary: str = ''
    constraints_applied: List[str] = None
    
    # Quality
    quality_score: float = 0.0
    
    # Errors
    error: str = None


class CodeGenerationPipeline:
    """
    Enhanced code generation pipeline that:
    1. Searches library for existing code to reuse
    2. Researches best practices if generating new code
    3. Loads and applies constraints
    4. Generates code with enhanced prompts
    5. Saves to library for future reuse
    """
    
    def __init__(self, tenant_id: str = None):
        self.tenant_id = tenant_id
        self.library_search = LibrarySearchService(tenant_id)
        self.research_service = ResearchService()
        self.constraint_manager = ConstraintManager(tenant_id)
        self.prompt_builder = PromptBuilder()
    
    def search_library(
        self,
        request: GenerationRequest,
        min_score: float = 0.85
    ) -> Optional[LibraryItem]:
        """
        Search library for a matching item.
        """
        results = self.library_search.hybrid_search(
            query=request.description,
            item_type=request.item_type,
            language=request.language,
            limit=5
        )
        
        for result in results:
            if result.get('combined_score', 0) >= min_score:
                try:
                    item = LibraryItem.objects.get(id=result['id'])
                    return item
                except LibraryItem.DoesNotExist:
                    continue
        
        return None
    
    async def gather_research(
        self,
        request: GenerationRequest
    ) -> dict:
        """
        Gather research for code generation.
        """
        return await self.research_service.research_topic(
            topic=request.description,
            language=request.language,
            include_web=True,
            include_github=True,
            include_packages=True
        )
    
    def get_constraints(
        self,
        request: GenerationRequest
    ) -> str:
        """
        Get applicable constraints for the request.
        """
        return self.constraint_manager.get_constraint_prompt(
            language=request.language,
            item_type=request.item_type
        )
    
    async def generate_code(
        self,
        request: GenerationRequest,
        research: dict = None,
        constraints: str = None
    ) -> str:
        """
        Generate code using Anthropic Claude with enhanced context.
        """
        # Build enhanced prompt
        prompt = self.prompt_builder.build_generation_prompt(
            description=request.description,
            language=request.language,
            item_type=request.item_type,
            research=research,
            constraints=constraints,
            existing_code=request.existing_code
        )
        
        # Call Anthropic Claude API
        import httpx
        
        api_key = getattr(settings, 'ANTHROPIC_API_KEY', None)
        
        if not api_key:
            logger.warning("Anthropic not configured, returning mock code")
            return self._get_mock_code(request)
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    'https://api.anthropic.com/v1/messages',
                    headers={
                        'x-api-key': api_key,
                        'Content-Type': 'application/json',
                        'anthropic-version': '2023-06-01',
                    },
                    json={
                        'model': 'claude-sonnet-4-20250514',
                        'max_tokens': 4000,
                        'system': self.prompt_builder.get_system_prompt(
                            request.language
                        ),
                        'messages': [
                            {'role': 'user', 'content': prompt}
                        ],
                        'temperature': 0.7,
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                content = data['content'][0]['text']
                
                # Extract code from markdown blocks
                code = self._extract_code(content, request.language)
                
                return code
                
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            raise
    
    def _extract_code(self, content: str, language: str) -> str:
        """Extract code from markdown response."""
        import re
        
        # Try to find code block with language
        pattern = rf'```{language}\s*\n(.*?)\n```'
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
        
        if matches:
            return matches[0].strip()
        
        # Try any code block
        pattern = r'```\w*\s*\n(.*?)\n```'
        matches = re.findall(pattern, content, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # Return content as-is
        return content.strip()
    
    def _get_mock_code(self, request: GenerationRequest) -> str:
        """Generate mock code for testing."""
        if request.language == 'typescript':
            return f'''
import React from 'react';

interface Props {{
  // Add props here
}}

export const {request.description.replace(' ', '')}Component: React.FC<Props> = (props) => {{
  return (
    <div>
      <h1>{request.description}</h1>
      {{/* Implementation here */}}
    </div>
  );
}};

export default {request.description.replace(' ', '')}Component;
'''
        elif request.language == 'python':
            return f'''
"""
{request.description}
"""

class {request.description.replace(' ', '')}Service:
    """Service for {request.description.lower()}."""
    
    def __init__(self):
        pass
    
    def execute(self):
        """Execute the main functionality."""
        # Implementation here
        pass


# Usage example
if __name__ == "__main__":
    service = {request.description.replace(' ', '')}Service()
    service.execute()
'''
        else:
            return f"// {request.description}\n// TODO: Implement"
    
    def save_to_library(
        self,
        code: str,
        request: GenerationRequest
    ) -> LibraryItem:
        """
        Save generated code to the library.
        """
        # Generate embedding
        embedding = embed_code_sync(code, request.description)
        
        # Create slug from description
        import re
        slug = re.sub(r'[^a-z0-9]+', '-', request.description.lower())[:100]
        
        # Check for existing item with same slug
        existing = LibraryItem.objects.filter(
            tenant_id=request.tenant_id,
            slug=slug
        ).first()
        
        if existing:
            # Create new version
            version_count = existing.versions.count()
            new_version = f"1.{version_count}.0"
            
            LibraryVersion.objects.create(
                item=existing,
                version=new_version,
                code=code,
                changelog=f"Auto-generated update",
            )
            
            # Update the item
            existing.code = code
            existing.embedding = embedding
            existing.save()
            
            return existing
        
        # Create new item
        item = LibraryItem.objects.create(
            tenant_id=request.tenant_id,
            name=request.description[:200],
            slug=slug,
            item_type=request.item_type,
            language=request.language,
            code=code,
            description=f"Auto-generated: {request.description}",
            embedding=embedding,
            source='generated',
            created_by_id=request.user_id,
            quality_score=70.0,  # Default score
        )
        
        # Create initial version
        LibraryVersion.objects.create(
            item=item,
            version="1.0.0",
            code=code,
            changelog="Initial generation",
        )
        
        return item
    
    async def run(self, request: GenerationRequest) -> GenerationResult:
        """
        Run the full generation pipeline.
        """
        result = GenerationResult(success=False)
        
        try:
            # Step 1: Search library for existing code
            if request.search_library:
                existing_item = self.search_library(request)
                
                if existing_item:
                    logger.info(f"Found matching library item: {existing_item.name}")
                    existing_item.increment_usage()
                    
                    return GenerationResult(
                        success=True,
                        code=existing_item.code,
                        from_library=True,
                        library_item_id=str(existing_item.id),
                        quality_score=existing_item.quality_score,
                    )
            
            # Step 2: Gather research
            research = None
            if request.do_research:
                research = await self.gather_research(request)
                result.research_summary = research.get('summary', '')
            
            # Step 3: Load constraints
            constraints = None
            if request.apply_constraints:
                constraints = self.get_constraints(request)
                result.constraints_applied = [c.name for c in 
                    self.constraint_manager.get_applicable_constraints(
                        language=request.language,
                        item_type=request.item_type
                    )
                ]
            
            # Step 4: Generate code
            code = await self.generate_code(request, research, constraints)
            
            if not code:
                result.error = "Failed to generate code"
                return result
            
            result.code = code
            result.success = True
            
            # Step 5: Save to library
            if request.save_to_library and code:
                try:
                    item = self.save_to_library(code, request)
                    result.library_item_id = str(item.id)
                    result.quality_score = item.quality_score
                except Exception as e:
                    logger.error(f"Error saving to library: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            result.error = str(e)
            return result


def generate_code_sync(request: GenerationRequest) -> GenerationResult:
    """
    Synchronous wrapper for code generation.
    """
    import asyncio
    
    pipeline = CodeGenerationPipeline(request.tenant_id)
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(pipeline.run(request))






