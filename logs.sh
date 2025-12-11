#!/bin/bash

# Simple colored log viewer

cd /tmp/faibric

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║              📊 FAIBRIC LIVE LOGS - SIMPLE VIEW               ║"
echo "║                  Press Ctrl+C to stop                          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Show last 10 lines from each service
echo "📝 RECENT LOGS:"
echo "────────────────────────────────────────────────────────────────"
docker-compose logs --tail=5 2>&1 | head -30
echo "────────────────────────────────────────────────────────────────"
echo ""
echo "🔄 LIVE STREAM (new logs appear below):"
echo ""

# Follow logs with colored output
docker-compose logs -f --tail=0 2>&1 | while IFS= read -r line; do
    TIME=$(date '+[%H:%M:%S]')
    
    # Filter and colorize important events
    if [[ $line == *"deploy_app_task"*"received"* ]]; then
        echo "$TIME 🚀 DEPLOYMENT STARTED"
    elif [[ $line == *"deploy_app_task"*"succeeded"* ]]; then
        echo "$TIME ✅ DEPLOYMENT COMPLETED"
    elif [[ $line == *"generate_app_task"*"received"* ]]; then
        echo "$TIME 🤖 AI GENERATION STARTED"
    elif [[ $line == *"generate_app_task"*"succeeded"* ]]; then
        echo "$TIME ✅ AI GENERATION COMPLETED"  
    elif [[ $line == *"Building image"* ]]; then
        echo "$TIME 🐳 Building Docker image..."
    elif [[ $line == *"Image built"* ]]; then
        echo "$TIME ✅ Image built"
    elif [[ $line == *"Container created"* ]]; then
        echo "$TIME ✅ Container started"
    elif [[ $line == *"POST"*"projects"* ]] && [[ $line == *"201"* ]]; then
        echo "$TIME 📝 New project created"
    elif [[ $line == *"POST"*"publish"* ]]; then
        echo "$TIME 🚀 Deploy request"
    elif [[ $line == *"openai.com"* ]]; then
        echo "$TIME 🧠 AI API call"
    elif [[ $line == *"ERROR"* ]] || [[ $line == *"Error"* ]] || [[ $line == *"Failed"* ]]; then
        echo "$TIME ❌ $(echo $line | cut -c1-100)"
    elif [[ $line == *"celery"* ]] && [[ $line == *"INFO"* ]]; then
        echo "$TIME 🔄 $(echo $line | grep -oP '(?<=INFO/MainProcess\] ).*' | cut -c1-80)"
    elif [[ $line == *"backend"* ]] && [[ $line =~ (GET|POST|PUT|DELETE) ]]; then
        METHOD=$(echo $line | grep -oP '(GET|POST|PUT|DELETE)')
        PATH=$(echo $line | grep -oP '(GET|POST|PUT|DELETE) \K[^ ]*')
        echo "$TIME 🌐 $METHOD $PATH"
    fi
done

