"""
Embeddings service for code library semantic search.
Uses OpenAI's text-embedding models.
"""
import hashlib
import logging
from typing import List, Optional

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating and working with text embeddings.
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'OPENAI_API_KEY', None)
        self.model = 'text-embedding-3-small'
        self.dimensions = 1536  # Default for text-embedding-3-small
        self.enabled = bool(self.api_key)
    
    async def embed_text(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text.
        """
        if not self.enabled:
            logger.warning("OpenAI not configured, returning mock embedding")
            return self._get_mock_embedding(text)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    'https://api.openai.com/v1/embeddings',
                    headers={
                        'Authorization': f'Bearer {self.api_key}',
                        'Content-Type': 'application/json',
                    },
                    json={
                        'model': self.model,
                        'input': text,
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data['data'][0]['embedding']
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    async def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts.
        """
        if not self.enabled:
            return [self._get_mock_embedding(t) for t in texts]
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    'https://api.openai.com/v1/embeddings',
                    headers={
                        'Authorization': f'Bearer {self.api_key}',
                        'Content-Type': 'application/json',
                    },
                    json={
                        'model': self.model,
                        'input': texts,
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # Sort by index to maintain order
                embeddings = [None] * len(texts)
                for item in data['data']:
                    embeddings[item['index']] = item['embedding']
                
                return embeddings
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            return [None] * len(texts)
    
    def _get_mock_embedding(self, text: str) -> List[float]:
        """
        Generate a deterministic mock embedding for testing.
        """
        import random
        
        # Use text hash as seed for deterministic results
        seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        # Generate random embedding
        return [random.uniform(-1, 1) for _ in range(self.dimensions)]
    
    def cosine_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        """
        import math
        
        if len(embedding1) != len(embedding2):
            raise ValueError("Embeddings must have same dimensions")
        
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = math.sqrt(sum(a * a for a in embedding1))
        norm2 = math.sqrt(sum(b * b for b in embedding2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def find_similar(
        self,
        query_embedding: List[float],
        candidates: List[dict],
        top_k: int = 10,
        min_score: float = 0.5
    ) -> List[dict]:
        """
        Find similar items from a list of candidates.
        
        Each candidate should have:
        - 'id': unique identifier
        - 'embedding': the embedding vector
        - Other fields to return
        """
        results = []
        
        for candidate in candidates:
            if not candidate.get('embedding'):
                continue
            
            score = self.cosine_similarity(
                query_embedding,
                candidate['embedding']
            )
            
            if score >= min_score:
                results.append({
                    **candidate,
                    'similarity_score': score
                })
        
        # Sort by score descending
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return results[:top_k]


def embed_code_sync(code: str, description: str = '') -> Optional[List[float]]:
    """
    Synchronous wrapper for embedding code.
    Combines code with description for better semantic understanding.
    """
    import asyncio
    
    service = EmbeddingService()
    
    # Combine code and description for richer embedding
    text = f"{description}\n\n```\n{code[:5000]}\n```"  # Limit code length
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(service.embed_text(text))


def embed_query_sync(query: str) -> Optional[List[float]]:
    """
    Synchronous wrapper for embedding a search query.
    """
    import asyncio
    
    service = EmbeddingService()
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(service.embed_text(query))


class CodeEmbedder:
    """
    Specialized embedder for code that extracts meaningful features.
    """
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
    
    def prepare_code_text(
        self,
        code: str,
        name: str = '',
        description: str = '',
        language: str = '',
        keywords: List[str] = None
    ) -> str:
        """
        Prepare code for embedding by combining with metadata.
        """
        parts = []
        
        if name:
            parts.append(f"Name: {name}")
        
        if description:
            parts.append(f"Description: {description}")
        
        if language:
            parts.append(f"Language: {language}")
        
        if keywords:
            parts.append(f"Keywords: {', '.join(keywords)}")
        
        # Add code with language hint
        parts.append(f"\n```{language}\n{code[:5000]}\n```")
        
        return '\n'.join(parts)
    
    async def embed_library_item(self, item) -> Optional[List[float]]:
        """
        Generate embedding for a LibraryItem.
        """
        text = self.prepare_code_text(
            code=item.code,
            name=item.name,
            description=item.description,
            language=item.language,
            keywords=item.keywords or []
        )
        
        return await self.embedding_service.embed_text(text)
    
    async def update_item_embedding(self, item) -> bool:
        """
        Update the embedding for a library item.
        """
        embedding = await self.embed_library_item(item)
        
        if embedding:
            item.embedding = embedding
            item.embedding_model = self.embedding_service.model
            await item.asave(update_fields=['embedding', 'embedding_model'])
            return True
        
        return False






