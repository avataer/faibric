# 🚀 Deploy Your New Faibric

## What You Have Now

A completely redesigned product creation experience with:
- Single input field → Live product in seconds
- Real-time AI reasoning chat
- Auto-deployment (no buttons needed)
- Split-screen view with actual running product

## Quick Start

```bash
cd ~/Code/Faibric

# 1. Make sure your OpenAI API key is set
nano .env
# Add: OPENAI_API_KEY=sk-...

# 2. Start everything
docker-compose down  # Stop old version if running
docker-compose up -d --build

# 3. Wait for services (30 seconds)
sleep 30

# 4. Run migrations
docker-compose exec backend python manage.py migrate

# 5. Create user (if needed)
docker-compose exec backend python manage.py createsuperuser

# 6. Access the new experience
open http://localhost:5173/create
```

## The New Flow

### Step 1: Landing Page
```
┌─────────────────────────────────────┐
│                                     │
│         Build Anything              │
│                                     │
│  ┌────────────────────────────┐    │
│  │ Describe what you want to  │    │
│  │ build...                   │ 🚀 │
│  └────────────────────────────┘    │
│                                     │
└─────────────────────────────────────┘
```

### Step 2: Live Creation (Split Screen)
```
┌─────────────────────────────────────────────────────────┐
│ ┌──────────────────────┐ ┌─────────────────────────┐   │
│ │                      │ │  AI Building Process    │   │
│ │   LIVE PRODUCT       │ │  ────────────────────   │   │
│ │   (iframe)           │ │                         │   │
│ │                      │ │  • Initializing AI...   │   │
│ │   Your actual        │ │  • Planning models...   │   │
│ │   running website/   │ │  • Creating User model  │   │
│ │   app appears here   │ │  • Building APIs...     │   │
│ │   in real-time       │ │  • Generating UI...     │   │
│ │                      │ │  • Deploying...         │   │
│ │                      │ │  • 🎉 Live!            │   │
│ │                      │ │                         │   │
│ └──────────────────────┘ └─────────────────────────┘   │
│  Left: Product          Right: AI Chat                  │
└─────────────────────────────────────────────────────────┘
```

## File Structure

```
~/Code/Faibric/
├── frontend/src/pages/
│   ├── CreateProduct.tsx     # NEW: Single input landing
│   ├── LiveCreation.tsx      # NEW: Split-screen view
│   └── App.tsx               # Updated routes
│
├── backend/apps/
│   ├── ai_engine/tasks.py    # Auto-deployment added
│   └── deployment/tasks.py   # Progress broadcasting
│
└── Documentation:
    ├── NEW_FLOW_SUMMARY.md
    └── DEPLOYMENT_INSTRUCTIONS.md (this file)
```

## Key Features

### 1. Auto-Generated Project Name
No need to think of names - auto-generated as `Project {timestamp}`

### 2. Auto-Deployment
Generation complete → Deployment starts immediately
No "Deploy" button needed

### 3. Real-Time Updates
- Progress updates every 2 seconds
- AI messages appear as they happen
- Iframe loads as soon as app is live

### 4. Live Product Display
- Shows actual running application
- Not a preview or mockup
- Real iframe with working product

## Testing the Flow

### Example 1: Portfolio Website
```
Input: "A portfolio website for a photographer with gallery and contact form"

Watch as:
1. AI analyzes requirements
2. Creates Gallery, Photo, Contact models
3. Builds REST APIs
4. Generates React components
5. Deploys to Docker
6. Shows live at username-project.localhost
```

### Example 2: Todo App
```
Input: "Todo app with tasks, categories, and due dates"

Result:
- Live todo application
- Full CRUD operations
- Categories and dates
- Beautiful UI
```

## Troubleshooting

### Frontend Won't Build
```bash
cd ~/Code/Faibric/frontend
npm install
cd ..
docker-compose restart frontend
```

### Can't See Live Product
Check deployment:
```bash
docker ps | grep "app-"
docker-compose logs celery | tail -20
```

### AI Generation Fails
Check OpenAI key:
```bash
docker-compose exec backend python -c "import os; print(os.getenv('OPENAI_API_KEY')[:20])"
```

## What's Different From Old Version

| Old | New |
|-----|-----|
| Project name field | Auto-generated |
| Description field | Removed |
| Template selection | Removed |
| Deploy button | Auto-deploys |
| Preview screen | Live product |
| Manual steps | Zero manual steps |

## Production Deployment

To deploy to production server:

1. Update `.env`:
```bash
APP_SUBDOMAIN_BASE=yourdomain.com
DEBUG=0
SECRET_KEY=<strong-secret-key>
```

2. Update `docker-compose.yml`:
```yaml
# Add SSL certificates for Traefik
# Configure proper domain routing
# Set resource limits appropriately
```

3. Deploy:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Success Indicators

✅ Can access http://localhost:5173/create
✅ Single text input visible
✅ After submit, split screen appears
✅ AI messages appear on right
✅ Live product loads on left (iframe)
✅ URL shows deployment address
✅ Product is actually functional

## Next Steps

1. Test the new flow
2. Gather user feedback
3. Add more AI reasoning visibility
4. Implement streaming responses (future)
5. Add product editing in-place

---

**You're ready! Just run the Quick Start commands above.** 🎉
