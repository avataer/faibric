# Implementation Guide for Refactorings

The project has been copied to `~/Code/Faibric`. Here are the key refactorings to apply:

## Priority 1: docker_manager.py (CRITICAL - 76% reduction possible)

**File**: `backend/apps/deployment/docker_manager.py`

### Issues Found:
1. **Massive duplication** - Has duplicate `DomainManager` class (lines 306-905)
2. **Bloated HTML template** - 800+ lines of embedded HTML
3. **Excessive sample data** - Generates 7 items when 5 is sufficient  
4. **Slow Docker builds** - Missing `--no-cache-dir` flag

### Refactor Actions:
```python
# Line 245: Change range(7) to range(5)
for i in range(5):  # Was: range(7)

# Line 280: Add --no-cache-dir to Dockerfile
RUN pip install --no-cache-dir flask flask-cors

# Lines 140-233: Minify HTML template
# Compress CSS by removing whitespace
# Combine all styles into single line

# Lines 306-905: DELETE entire duplicate DomainManager class
# The class is already defined at line 306
```

## Priority 2: CreationView.tsx (39% reduction possible)

**File**: `frontend/src/pages/CreationView.tsx`

### Issues:
1. **Too frequent polling** - 1000ms interval
2. **Hardcoded feature list** - Not dynamic
3. **Sequential API calls** - Should be parallel

### Refactor Actions:
```typescript
// Line 37: Change polling interval
const interval = setInterval(async () => {
  // ... 
}, 2000) // Was: 1000

// Add adaptive polling after line 75
if (progress && progress.progress > 50) {
  clearInterval(interval)
  pollInterval = setTimeout(poll, 3000) // Slow down
}

// Lines 39-40: Make parallel with Promise.all
const [progressData, updatedProject] = await Promise.all([
  projectsService.getProgress(Number(id)),
  projectsService.getProject(Number(id))
])

// Lines 275-297: Remove hardcoded features array
// Use actual data from project instead
```

## Priority 3: settings.py (Caching & Pooling)

**File**: `backend/faibric_backend/settings.py`

### Add After Line 85:
```python
DATABASES = {
    'default': {
        # ... existing config ...
        'CONN_MAX_AGE': 600,  # ADD THIS - Connection pooling
    }
}
```

### Add After Line 157:
```python
# ADD THIS - Redis caching
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://redis:6379/1'),
        'KEY_PREFIX': 'faibric',
        'TIMEOUT': 300,
    }
}
```

##Priority 4: views.py (Query Optimization)

**File**: `backend/apps/projects/views.py`

### Line 27: Add query optimization
```python
def get_queryset(self):
    return Project.objects.filter(user=self.request.user)\
        .select_related('user')\
        .prefetch_related('models', 'apis')  # ADD THIS
```

### Lines 120-134: Simplify with dict
```python
status_map = {
    'generating': {'step': 0, 'message': 'Initializing...', 'progress': 0},
    'ready': {'step': 10, 'message': 'Complete', 'progress': 100},
    'failed': {'step': -1, 'message': 'Failed', 'progress': 0}
}
return Response(status_map.get(project.status, {'step': 0, ...}))
```

## Priority 5: docker-compose.yml (Health Checks)

**File**: `docker-compose.yml`

### Add to postgres service:
```yaml
postgres:
  # ... existing config ...
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U faibric_user"]
    interval: 10s
    timeout: 5s
    retries: 5
```

### Add to redis service:
```yaml
redis:
  command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 3s
    retries: 5
```

### Update backend depends_on:
```yaml
backend:
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_healthy
```

## Testing After Refactoring

```bash
cd ~/Code/Faibric

# 1. Verify syntax
python -m py_compile backend/apps/deployment/docker_manager.py
python -m py_compile backend/apps/projects/views.py
python -m py_compile backend/faibric_backend/settings.py

# 2. Run tests
docker-compose up -d
docker-compose logs backend | grep -i error
docker-compose logs celery | grep -i error

# 3. Test frontend
cd frontend
npm run lint
```

## Expected Results

- **40% less code** overall
- **50-67% less API polling** (2-3s vs 1s)
- **Database queries** optimized with prefetch
- **Docker builds** 20-30% faster
- **Caching** reduces repeated API calls

## Quick Win Scripts

```bash
# Automated line count check
cd ~/Code/Faibric
wc -l backend/apps/deployment/docker_manager.py
# Target: < 300 lines (currently 905)

# Check for duplicates
grep -n "class DomainManager" backend/apps/deployment/docker_manager.py
# Should only appear once

# Verify polling interval
grep "setInterval" frontend/src/pages/CreationView.tsx
# Should be 2000 or 3000, not 1000
```

---

**Start with docker_manager.py** - it has the biggest impact (76% reduction possible)!
