# Faibric V2 - Complete System Redesign

## Executive Summary

Faibric is an AI-powered platform where customers enter a prompt describing what they want built, and the system generates it in real-time. The current architecture is over-engineered, slow, and unreliable. This document outlines a complete redesign focused on **speed, reliability, and code reuse**.

---

## Current Problems

### 1. **Architecture Over-Engineering**
- Generates Django models, serializers, viewsets, AND React components for every project
- 90% of user requests don't need a database backend
- Sequential AI calls make generation slow (5-7 API calls per project)

### 2. **Slow AI Orchestration**
- Multiple sequential AI calls: analyze → models → serializers → viewsets → components
- No streaming - users see nothing until each step completes
- Generic prompts that produce inconsistent results

### 3. **No Code Reuse**
- Template model exists but isn't used
- Same components get regenerated repeatedly
- No learning from previous generations

### 4. **Deployment Complexity**
- Full Docker builds from scratch every time (slow)
- No caching of npm dependencies
- Production nginx builds for every quick change

### 5. **Poor Real-Time Communication**
- Redis cache polling instead of WebSockets
- 500ms polling interval = delayed updates
- No true streaming of AI responses

---

## V2 Architecture

### Core Principle: **Frontend-First, Backend-Optional**

Most user requests are for:
- Static websites
- Single-page apps
- Interactive tools (calculators, converters)
- Simple dashboards

These **don't need a backend**. The new architecture assumes frontend-only by default and adds backend only when explicitly needed.

---

## New System Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FAIBRIC V2                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │   FRONTEND   │────▶│   GATEWAY    │────▶│   AI ENGINE  │        │
│  │   (React)    │◀────│   (FastAPI)  │◀────│   (Async)    │        │
│  └──────────────┘     └──────────────┘     └──────────────┘        │
│         │                    │                    │                  │
│         │              WebSocket            ┌─────┴─────┐           │
│         │              Streaming            │           │           │
│         ▼                    │              ▼           ▼           │
│  ┌──────────────┐     ┌──────────────┐  ┌──────┐  ┌──────────┐    │
│  │  LIVE VIEW   │     │    REDIS     │  │OPENAI│  │  CLAUDE  │    │
│  │   (iframe)   │     │  (Pub/Sub)   │  │ API  │  │   API    │    │
│  └──────────────┘     └──────────────┘  └──────┘  └──────────┘    │
│         │                    │                                      │
│         │                    ▼                                      │
│         │             ┌──────────────┐                             │
│         │             │   POSTGRES   │                             │
│         │             │  (Projects)  │                             │
│         │             └──────────────┘                             │
│         │                    │                                      │
│         ▼                    ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │                    CODE REPOSITORY                        │     │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐     │     │
│  │  │Templates│  │Components│  │ Themes  │  │Databases│     │     │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘     │     │
│  └──────────────────────────────────────────────────────────┘     │
│         │                                                          │
│         ▼                                                          │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │                   DEPLOYMENT ENGINE                       │     │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │     │
│  │  │Static Hosts │  │ Docker Apps │  │ K8s Deploys │       │     │
│  │  │  (Instant)  │  │ (Backends)  │  │ (Scale)     │       │     │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │     │
│  └──────────────────────────────────────────────────────────┘     │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Core Rewrite (Week 1)

#### 1.1 New AI Engine

Replace the current multi-step generation with a **single-shot** approach:

```python
# NEW: backend/apps/ai_engine/v2/generator.py

from openai import OpenAI
import anthropic
from typing import AsyncGenerator
import json

class AIGenerator:
    """
    Single-shot app generator with streaming
    """
    
    def __init__(self, model: str = "gpt-4o"):
        self.openai = OpenAI()
        self.anthropic = anthropic.Anthropic()
        self.model = model
    
    async def generate_app_stream(
        self, 
        prompt: str, 
        project_id: int
    ) -> AsyncGenerator[dict, None]:
        """
        Stream the entire app generation as a single prompt.
        Yields messages for real-time UI updates.
        """
        
        # Determine app type from prompt
        app_type = await self._classify_prompt(prompt)
        
        yield {"type": "thinking", "content": f"Building a {app_type}..."}
        
        # Get the appropriate system prompt
        system_prompt = self._get_system_prompt(app_type)
        
        # Single AI call with streaming
        async for chunk in self._stream_generation(system_prompt, prompt):
            yield chunk
    
    def _get_system_prompt(self, app_type: str) -> str:
        """Get specialized prompt based on app type"""
        
        prompts = {
            "website": WEBSITE_PROMPT,
            "webapp": WEBAPP_PROMPT,
            "tool": TOOL_PROMPT,
            "dashboard": DASHBOARD_PROMPT,
            "game": GAME_PROMPT,
            "form": FORM_PROMPT,
        }
        return prompts.get(app_type, GENERIC_PROMPT)
    
    async def _stream_generation(
        self, 
        system: str, 
        user: str
    ) -> AsyncGenerator[dict, None]:
        """Stream AI generation with real-time updates"""
        
        stream = self.openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            stream=True,
            response_format={"type": "json_object"}
        )
        
        buffer = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                buffer += chunk.choices[0].delta.content
                
                # Try to parse partial JSON for progress updates
                progress = self._extract_progress(buffer)
                if progress:
                    yield {"type": "progress", "content": progress}
        
        # Parse final result
        result = json.loads(buffer)
        yield {"type": "complete", "content": result}
```

#### 1.2 Specialized Generation Prompts

```python
# NEW: backend/apps/ai_engine/v2/prompts.py

WEBSITE_PROMPT = """You are an expert web developer creating a complete React website.

OUTPUT FORMAT (JSON):
{
    "app_type": "website",
    "title": "Page Title",
    "description": "SEO description",
    "components": {
        "App.tsx": "// Complete App.tsx code",
        "components/Header.tsx": "// Header component",
        "components/Hero.tsx": "// Hero section",
        "components/Content.tsx": "// Main content",
        "components/Footer.tsx": "// Footer"
    },
    "styles": {
        "colors": {"primary": "#hex", "secondary": "#hex", "background": "#hex", "text": "#hex"},
        "fonts": {"heading": "font-family", "body": "font-family"}
    },
    "data": {
        // Any hardcoded data the components need
    }
}

RULES:
1. Use ONLY inline styles (no external CSS imports)
2. Generate REAL content - no placeholders like "Lorem ipsum"
3. Make it visually stunning with proper spacing, shadows, gradients
4. Include responsive design (use flexbox/grid)
5. All components must be self-contained TypeScript/React
6. NO external dependencies except React itself

The user wants:
"""

TOOL_PROMPT = """You are an expert React developer creating an interactive tool/calculator.

OUTPUT FORMAT (JSON):
{
    "app_type": "tool",
    "title": "Tool Name",
    "components": {
        "App.tsx": "// Complete working tool code"
    },
    "features": ["feature1", "feature2"],
    "styles": {
        "colors": {"primary": "#hex", "accent": "#hex", "background": "#hex"},
        "theme": "light|dark"
    }
}

RULES:
1. Tool must be FULLY FUNCTIONAL with real calculations/logic
2. Include input validation
3. Beautiful, modern UI with inline styles only
4. Clear user feedback for all interactions
5. Mobile-responsive design

The user wants:
"""

WEBAPP_WITH_BACKEND_PROMPT = """You are an expert full-stack developer creating a complete web application.

OUTPUT FORMAT (JSON):
{
    "app_type": "webapp",
    "requires_backend": true,
    "frontend": {
        "components": {
            "App.tsx": "// Main app with routing",
            "pages/Home.tsx": "// Home page",
            "pages/Dashboard.tsx": "// Dashboard",
            "components/Navbar.tsx": "// Navigation"
        }
    },
    "backend": {
        "models": [
            {
                "name": "ModelName",
                "fields": [
                    {"name": "field", "type": "CharField", "options": {}}
                ]
            }
        ],
        "api": [
            {"path": "/api/resource", "method": "GET", "description": "..."}
        ]
    },
    "database": {
        "type": "postgresql",
        "schema": "// SQL schema"
    }
}

The user wants:
"""
```

#### 1.3 WebSocket Real-Time Communication

Replace polling with WebSockets:

```python
# NEW: backend/apps/realtime/consumers.py

from channels.generic.websocket import AsyncWebsocketConsumer
import json

class ProjectConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time project updates"""
    
    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.group_name = f'project_{self.project_id}'
        
        # Join project group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Handle incoming messages (user chat)"""
        data = json.loads(text_data)
        
        if data['type'] == 'user_message':
            # Process user's modification request
            await self.process_modification(data['content'])
    
    async def generation_update(self, event):
        """Send generation updates to client"""
        await self.send(text_data=json.dumps({
            'type': event['message_type'],
            'content': event['content'],
            'timestamp': event['timestamp']
        }))
    
    async def process_modification(self, user_request):
        """Process a modification request from user"""
        from apps.ai_engine.v2.generator import AIGenerator
        
        generator = AIGenerator()
        
        async for update in generator.modify_app_stream(
            project_id=self.project_id,
            request=user_request
        ):
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'generation_update',
                    'message_type': update['type'],
                    'content': update['content'],
                    'timestamp': update.get('timestamp')
                }
            )
```

### Phase 2: Code Repository System (Week 2)

#### 2.1 New Database Models

```python
# NEW: backend/apps/repository/models.py

from django.db import models

class CodeTemplate(models.Model):
    """Reusable code templates"""
    
    CATEGORIES = [
        ('layout', 'Page Layout'),
        ('component', 'UI Component'),
        ('page', 'Full Page'),
        ('tool', 'Interactive Tool'),
        ('theme', 'Color Theme'),
        ('database', 'Database Schema'),
        ('api', 'API Endpoint'),
    ]
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=50, choices=CATEGORIES)
    description = models.TextField()
    
    # The actual code
    code = models.TextField()
    
    # What this template provides
    provides = models.JSONField(default=list)  # ['navigation', 'footer', 'hero']
    
    # What this template requires
    requires = models.JSONField(default=list)  # ['react', 'typescript']
    
    # Usage tracking for learning
    usage_count = models.IntegerField(default=0)
    success_rate = models.FloatField(default=1.0)  # 0-1 based on user feedback
    
    # Embedding for semantic search
    embedding = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-success_rate', '-usage_count']


class ComponentLibrary(models.Model):
    """Generated components that can be reused"""
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    
    # Component code
    code = models.TextField()
    
    # Component props/interface
    props_interface = models.JSONField(default=dict)
    
    # Style variants
    variants = models.JSONField(default=dict)
    
    # Source project (where this was first generated)
    source_project = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        null=True,
        related_name='contributed_components'
    )
    
    # Quality metrics
    usage_count = models.IntegerField(default=0)
    rating = models.FloatField(default=0)
    
    # Embedding for semantic search
    embedding = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)


class DatabaseSchema(models.Model):
    """Reusable database schemas"""
    
    name = models.CharField(max_length=200)  # e.g., "E-commerce", "Blog", "CRM"
    description = models.TextField()
    
    # Schema definition
    tables = models.JSONField()  # [{name, fields, relationships}]
    
    # SQL for different databases
    postgresql_sql = models.TextField()
    mysql_sql = models.TextField(blank=True)
    sqlite_sql = models.TextField(blank=True)
    
    # Associated API patterns
    api_patterns = models.JSONField(default=list)
    
    usage_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
```

#### 2.2 Semantic Search for Code Reuse

```python
# NEW: backend/apps/repository/search.py

from openai import OpenAI
import numpy as np
from typing import List
from .models import CodeTemplate, ComponentLibrary

class CodeSearchEngine:
    """Semantic search for finding reusable code"""
    
    def __init__(self):
        self.client = OpenAI()
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text"""
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    
    def find_similar_templates(
        self, 
        query: str, 
        category: str = None,
        limit: int = 5
    ) -> List[CodeTemplate]:
        """Find templates similar to the query"""
        
        query_embedding = self.get_embedding(query)
        
        templates = CodeTemplate.objects.all()
        if category:
            templates = templates.filter(category=category)
        
        # Calculate similarity scores
        scored = []
        for template in templates:
            if template.embedding:
                similarity = self._cosine_similarity(
                    query_embedding, 
                    template.embedding
                )
                scored.append((template, similarity))
        
        # Sort by similarity
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [t[0] for t in scored[:limit]]
    
    def find_reusable_components(
        self, 
        description: str,
        limit: int = 10
    ) -> List[ComponentLibrary]:
        """Find components that match a description"""
        
        query_embedding = self.get_embedding(description)
        
        scored = []
        for component in ComponentLibrary.objects.all():
            if component.embedding:
                similarity = self._cosine_similarity(
                    query_embedding,
                    component.embedding
                )
                # Weight by usage and rating
                score = similarity * (1 + component.usage_count * 0.01) * component.rating
                scored.append((component, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return [c[0] for c in scored[:limit]]
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between vectors"""
        a = np.array(a)
        b = np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
```

### Phase 3: Smart Deployment (Week 3)

#### 3.1 Tiered Deployment System

```python
# NEW: backend/apps/deployment/v2/deployer.py

from abc import ABC, abstractmethod
import docker
from typing import Dict, Any

class Deployer(ABC):
    """Base deployer interface"""
    
    @abstractmethod
    async def deploy(self, project: Any) -> str:
        """Deploy and return URL"""
        pass
    
    @abstractmethod
    async def update(self, project: Any, changes: Dict) -> bool:
        """Hot-update deployment"""
        pass


class StaticDeployer(Deployer):
    """
    For frontend-only apps.
    Instant deployment via pre-built container with volume mount.
    """
    
    def __init__(self):
        self.client = docker.DockerClient()
        # Pre-built base image with Node, React, etc.
        self.base_image = "faibric/static-host:latest"
    
    async def deploy(self, project) -> str:
        """Deploy static app in ~2 seconds"""
        
        # Write files to shared volume
        app_dir = f"/apps/{project.id}"
        self._write_app_files(app_dir, project.frontend_code)
        
        # Start container from pre-built image
        container = self.client.containers.run(
            self.base_image,
            name=f"app-{project.id}",
            detach=True,
            volumes={app_dir: {'bind': '/app', 'mode': 'ro'}},
            labels=self._traefik_labels(project),
            network="faibric_deployed_apps"
        )
        
        return f"http://{project.subdomain}.localhost"
    
    async def update(self, project, changes: Dict) -> bool:
        """Hot-update by writing new files (no rebuild)"""
        app_dir = f"/apps/{project.id}"
        
        for filename, content in changes.items():
            filepath = f"{app_dir}/{filename}"
            with open(filepath, 'w') as f:
                f.write(content)
        
        # Trigger hot reload (the container watches for file changes)
        return True


class DockerDeployer(Deployer):
    """
    For apps that need a backend.
    Full Docker build with caching.
    """
    
    async def deploy(self, project) -> str:
        """Deploy full-stack app"""
        
        # Use cached layers for faster builds
        image = await self._build_image(project)
        
        container = self.client.containers.run(
            image,
            name=f"app-{project.id}",
            detach=True,
            labels=self._traefik_labels(project),
            network="faibric_deployed_apps",
            environment=self._get_env(project)
        )
        
        return f"http://{project.subdomain}.localhost"


class DeploymentOrchestrator:
    """
    Chooses the right deployment strategy based on app type
    """
    
    def __init__(self):
        self.static_deployer = StaticDeployer()
        self.docker_deployer = DockerDeployer()
    
    async def deploy(self, project) -> str:
        """Deploy using the appropriate strategy"""
        
        if self._needs_backend(project):
            return await self.docker_deployer.deploy(project)
        else:
            return await self.static_deployer.deploy(project)
    
    def _needs_backend(self, project) -> bool:
        """Determine if project needs a backend"""
        
        analysis = project.ai_analysis or {}
        
        # Check if backend is explicitly required
        if analysis.get('requires_backend'):
            return True
        
        # Check for database models
        if analysis.get('models') and len(analysis['models']) > 0:
            return True
        
        # Check for API endpoints
        if analysis.get('api_endpoints') and len(analysis['api_endpoints']) > 0:
            return True
        
        return False
```

### Phase 4: Frontend Rewrite (Week 4)

#### 4.1 New LiveCreation with WebSocket

```typescript
// NEW: frontend/src/pages/LiveCreation.tsx

import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import useWebSocket from 'react-use-websocket'

interface Message {
  type: 'thinking' | 'progress' | 'success' | 'error' | 'user'
  content: string
  timestamp: number
}

const LiveCreation = () => {
  const { id } = useParams<{ id: string }>()
  const [messages, setMessages] = useState<Message[]>([])
  const [deploymentUrl, setDeploymentUrl] = useState('')
  const [userInput, setUserInput] = useState('')
  const iframeRef = useRef<HTMLIFrameElement>(null)
  
  // WebSocket connection
  const { sendMessage, lastMessage, readyState } = useWebSocket(
    `ws://localhost:8000/ws/project/${id}/`,
    {
      onOpen: () => console.log('Connected to project'),
      shouldReconnect: () => true,
    }
  )
  
  // Handle incoming WebSocket messages
  useEffect(() => {
    if (lastMessage) {
      const data = JSON.parse(lastMessage.data)
      
      setMessages(prev => [...prev, {
        type: data.type,
        content: data.content,
        timestamp: Date.now()
      }])
      
      // Handle deployment complete
      if (data.type === 'deployed') {
        setDeploymentUrl(data.url)
        reloadIframe()
      }
    }
  }, [lastMessage])
  
  const handleSend = useCallback(() => {
    if (!userInput.trim()) return
    
    // Add user message to UI immediately
    setMessages(prev => [...prev, {
      type: 'user',
      content: userInput,
      timestamp: Date.now()
    }])
    
    // Send via WebSocket
    sendMessage(JSON.stringify({
      type: 'user_message',
      content: userInput
    }))
    
    setUserInput('')
  }, [userInput, sendMessage])
  
  const reloadIframe = () => {
    if (iframeRef.current && deploymentUrl) {
      iframeRef.current.src = `${deploymentUrl}?t=${Date.now()}`
    }
  }
  
  return (
    <div className="live-creation">
      {/* Left: Live Preview */}
      <div className="preview-panel">
        {deploymentUrl ? (
          <iframe 
            ref={iframeRef}
            src={deploymentUrl}
            title="Live Preview"
          />
        ) : (
          <BuildingAnimation messages={messages} />
        )}
      </div>
      
      {/* Right: AI Chat */}
      <div className="chat-panel">
        <div className="messages">
          {messages.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
          ))}
        </div>
        
        <div className="input-area">
          <input
            value={userInput}
            onChange={e => setUserInput(e.target.value)}
            onKeyPress={e => e.key === 'Enter' && handleSend()}
            placeholder="Request changes..."
          />
          <button onClick={handleSend}>Send</button>
        </div>
      </div>
    </div>
  )
}
```

---

## Database Schema Changes

### New Tables

```sql
-- Code Repository
CREATE TABLE code_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(200) UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    code TEXT NOT NULL,
    provides JSONB DEFAULT '[]',
    requires JSONB DEFAULT '[]',
    usage_count INTEGER DEFAULT 0,
    success_rate FLOAT DEFAULT 1.0,
    embedding JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE component_library (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    code TEXT NOT NULL,
    props_interface JSONB DEFAULT '{}',
    variants JSONB DEFAULT '{}',
    source_project_id INTEGER REFERENCES projects(id),
    usage_count INTEGER DEFAULT 0,
    rating FLOAT DEFAULT 0,
    embedding JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE database_schemas (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    tables JSONB NOT NULL,
    postgresql_sql TEXT NOT NULL,
    mysql_sql TEXT,
    sqlite_sql TEXT,
    api_patterns JSONB DEFAULT '[]',
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add indexes for search
CREATE INDEX idx_templates_category ON code_templates(category);
CREATE INDEX idx_templates_usage ON code_templates(usage_count DESC);
CREATE INDEX idx_components_rating ON component_library(rating DESC);
```

### Migration for Existing Projects Table

```sql
-- Add new columns to projects
ALTER TABLE projects ADD COLUMN app_type VARCHAR(50) DEFAULT 'website';
ALTER TABLE projects ADD COLUMN requires_backend BOOLEAN DEFAULT FALSE;
ALTER TABLE projects ADD COLUMN generation_version VARCHAR(10) DEFAULT 'v2';
ALTER TABLE projects ADD COLUMN reused_components JSONB DEFAULT '[]';
```

---

## API Changes

### New Endpoints

```python
# backend/faibric_backend/urls.py

urlpatterns = [
    # ... existing ...
    
    # V2 Generation API
    path('api/v2/generate/', views.GenerateAppView.as_view()),
    path('api/v2/projects/<int:id>/modify/', views.ModifyAppView.as_view()),
    
    # Code Repository API
    path('api/repository/templates/', views.TemplateListView.as_view()),
    path('api/repository/components/', views.ComponentListView.as_view()),
    path('api/repository/search/', views.SemanticSearchView.as_view()),
    
    # WebSocket
    path('ws/project/<int:project_id>/', consumers.ProjectConsumer.as_asgi()),
]
```

---

## Configuration Changes

### New Environment Variables

```bash
# .env

# AI Models
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...  # Optional: Claude as backup
DEFAULT_AI_MODEL=gpt-4o   # or gpt-4o-mini for cost savings

# Deployment
STATIC_APPS_VOLUME=/var/faibric/apps
DEPLOYMENT_STRATEGY=auto  # auto, static, docker

# Code Repository
ENABLE_CODE_REUSE=true
MIN_REUSE_SIMILARITY=0.85

# WebSocket
WEBSOCKET_URL=ws://localhost:8000
CHANNEL_LAYERS_BACKEND=channels_redis.core.RedisChannelLayer
```

### Updated docker-compose.yml

```yaml
version: '3.8'

services:
  # ... existing services ...
  
  # New: Channels/WebSocket support
  daphne:
    build: ./backend
    command: daphne -b 0.0.0.0 -p 8001 faibric_backend.asgi:application
    ports:
      - "8001:8001"
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
    networks:
      - faibric_network
  
  # Static app host (pre-built, instant deployments)
  static-host:
    image: faibric/static-host:latest
    volumes:
      - static_apps:/apps:ro
    networks:
      - deployed_apps
    labels:
      - "traefik.enable=true"

volumes:
  static_apps:
```

---

## Migration Path

### Step 1: Parallel Operation
- Deploy V2 alongside V1
- New projects use V2, existing use V1
- Monitor and compare

### Step 2: Data Migration
- Migrate successful projects to V2 format
- Extract reusable components to library
- Build initial template collection

### Step 3: Full Cutover
- Redirect all traffic to V2
- Deprecate V1 endpoints
- Archive V1 code

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Time to first preview | 30-60s | <5s |
| Full generation time | 2-5 min | <30s |
| Quick update time | 15-30s | <3s |
| AI API calls per project | 5-7 | 1-2 |
| Deployment time | 45s | <5s |
| Code reuse rate | 0% | >40% |
| User satisfaction | Unknown | >4.5/5 |

---

## Risk Mitigation

### Risk 1: AI Quality Degradation with Single-Shot
**Mitigation**: Use more detailed prompts, add validation layer, keep multi-shot as fallback.

### Risk 2: Code Reuse Introduces Bugs
**Mitigation**: Quality scoring, user feedback loop, automatic testing.

### Risk 3: WebSocket Scalability
**Mitigation**: Redis pub/sub, connection pooling, horizontal scaling.

---

## Immediate Next Steps

1. **Create base Docker images** for instant deployment
2. **Implement WebSocket infrastructure** (Django Channels)
3. **Build new AI generator** with streaming
4. **Create code repository schema** and seed initial templates
5. **Build new frontend** with WebSocket support
6. **Test end-to-end** with sample prompts
7. **Performance benchmark** vs current system
8. **Gradual rollout** starting with new users

---

## Timeline

| Week | Deliverable |
|------|-------------|
| 1 | Core AI engine rewrite, WebSocket infrastructure |
| 2 | Code repository system, semantic search |
| 3 | Smart deployment system, instant static hosting |
| 4 | Frontend rewrite, integration testing |
| 5 | Performance optimization, bug fixes |
| 6 | Beta launch, monitoring, iteration |

---

*Document Version: 1.0*
*Created: November 24, 2025*
*Author: AI Assistant*

