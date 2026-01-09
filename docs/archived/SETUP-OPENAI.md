# OpenAI API Key Setup

## The Issue
Your project creation failed because you don't have a valid OpenAI API key configured. The current key is just a placeholder: `sk-placeholder-key`

## How to Get an OpenAI API Key

1. **Go to OpenAI's platform**: https://platform.openai.com/
2. **Sign up or log in** to your account
3. **Navigate to API keys**: https://platform.openai.com/api-keys
4. **Create a new API key**:
   - Click "Create new secret key"
   - Give it a name (e.g., "Faibric Development")
   - Copy the key (it starts with `sk-`)
   - **IMPORTANT**: Save it immediately - you won't be able to see it again!

## How to Configure Your Key

### Method 1: Update .env file (Recommended)
```bash
# Edit the .env file
nano /tmp/faibric/.env

# Replace the placeholder with your real key
OPENAI_API_KEY=sk-your-actual-key-here
```

### Method 2: Direct Docker Compose restart
```bash
cd /tmp/faibric

# Export your key temporarily
export OPENAI_API_KEY=sk-your-actual-key-here

# Restart the services
docker-compose down
docker-compose up -d
```

## After Setting Up the Key

1. **Restart the services**:
```bash
cd /tmp/faibric
docker-compose restart backend celery
```

2. **Verify it's working**:
```bash
docker-compose exec backend env | grep OPENAI_API_KEY
```

3. **Try creating a project again** in the web interface

## Pricing Note
- OpenAI API usage is **pay-as-you-go**
- GPT-4 Turbo costs approximately $0.01-0.03 per request (depending on length)
- You can set usage limits in your OpenAI dashboard to prevent surprises
- First-time users often get free credits to get started

## Troubleshooting

### If you see "sk-placeholder-key":
The environment variable wasn't loaded properly. Make sure:
1. Your `.env` file is at `/tmp/faibric/.env`
2. You've restarted the services after editing
3. The docker-compose.yml file includes the `.env` file (it does)

### If project creation still fails:
Check the logs:
```bash
docker-compose logs celery | tail -50
```

Look for error messages about the API key or OpenAI.

