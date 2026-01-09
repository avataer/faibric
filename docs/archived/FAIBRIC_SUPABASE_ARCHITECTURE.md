# Faibric + Supabase Architecture

## The Industry Standard Approach

Modern AI app builders (Bolt.new, Lovable, v0.dev) all use **Supabase** as their backend-as-a-service. This solves:

1. **Database** - Each app gets PostgreSQL
2. **Authentication** - Users can sign up/login
3. **Real-time** - Live updates via subscriptions
4. **Storage** - File uploads
5. **Edge Functions** - Server-side logic

## Implementation Plan

### Phase 1: Supabase Integration (Immediate)

1. **Create Faibric Supabase Project**
   - One Supabase project for all Faibric-generated apps
   - Use Row Level Security (RLS) to isolate data per app

2. **Update AI Prompts**
   - Teach AI to use Supabase client
   - Generate code with `@supabase/supabase-js`

3. **Provide Supabase Keys**
   - Inject anon key into generated apps at build time
   - Service key stays on Faibric backend

### Phase 2: Per-App Supabase (Future)

- Each generated app gets its own Supabase project
- Full isolation between apps
- Requires Supabase Management API

---

## Code Changes Required

### 1. Environment Variables

```bash
# Add to docker-compose.yml backend environment
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJxxxx
SUPABASE_SERVICE_KEY=eyJxxxx  # Server-side only
```

### 2. Database Schema (in Supabase)

```sql
-- Apps table (tracks which data belongs to which app)
CREATE TABLE faibric_apps (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id INTEGER NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Generic data storage for any app
CREATE TABLE app_data (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  app_id UUID REFERENCES faibric_apps(id),
  table_name TEXT NOT NULL,
  data JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Row Level Security
ALTER TABLE app_data ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Apps can only access their own data"
  ON app_data
  FOR ALL
  USING (app_id = current_setting('app.current_app_id')::UUID);
```

### 3. Updated AI Prompts

```python
SUPABASE_INSTRUCTIONS = """
## Database & Backend with Supabase

For apps that need to SAVE DATA across users/sessions, use Supabase:

```javascript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'SUPABASE_URL',  // Injected at build time
  'SUPABASE_ANON_KEY'
)

// Save data
const { data, error } = await supabase
  .from('app_data')
  .insert({ table_name: 'news', data: { title: 'Hello', body: '...' } })

// Read data
const { data, error } = await supabase
  .from('app_data')
  .select('*')
  .eq('table_name', 'news')

// Real-time subscription
supabase
  .channel('news')
  .on('postgres_changes', { event: '*', schema: 'public', table: 'app_data' }, 
    (payload) => console.log(payload))
  .subscribe()
```

Use Supabase when:
- Data needs to persist across users
- Multiple users need to see the same data
- Real-time updates are needed

Use localStorage when:
- Data is user-specific and doesn't need to be shared
- Simple personal todos, notes, preferences
"""
```

### 4. Build-time Injection

When deploying an app, inject the Supabase credentials:

```python
# In fast_deployer.py
def _create_app_files(self, project, build_dir):
    # ... existing code ...
    
    # Inject Supabase config
    env_content = f"""
VITE_SUPABASE_URL={settings.SUPABASE_URL}
VITE_SUPABASE_ANON_KEY={settings.SUPABASE_ANON_KEY}
VITE_APP_ID={project.id}
"""
    (build_dir / '.env').write_text(env_content)
```

---

## What You Need To Do

### Step 1: Create Supabase Project (Free)

1. Go to https://supabase.com
2. Sign up / Log in
3. Create new project "Faibric"
4. Copy the URL and anon key from Settings > API

### Step 2: Give Me the Keys

Once you have them, I'll:
1. Add them to docker-compose.yml
2. Create the database schema
3. Update AI prompts
4. Test with a real multi-user app

---

## Benefits

| Feature | Before (localStorage) | After (Supabase) |
|---------|----------------------|------------------|
| Data persistence | Browser only | Cloud database |
| Multi-user | ❌ | ✅ |
| Real-time sync | ❌ | ✅ |
| Authentication | ❌ | ✅ |
| File uploads | ❌ | ✅ |

---

## Alternative: Self-hosted

If you don't want to use Supabase cloud:
- Self-host Supabase via Docker
- Or use plain PostgreSQL + PostgREST

But Supabase cloud is free for small projects and much easier.



