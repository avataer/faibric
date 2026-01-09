#!/bin/bash

# 📊 FAIBRIC REAL-TIME MONITORING DASHBOARD

clear

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║           🚀 FAIBRIC REAL-TIME LOGS & STATUS                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

cd /tmp/faibric

# Function to get container status
show_status() {
    echo "📊 SERVICES STATUS:"
    docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null | head -7
    echo ""
}

# Function to show recent activity
show_activity() {
    echo "📝 RECENT ACTIVITY (Last 30 seconds):"
    echo "─────────────────────────────────────────────────────────────────"
    
    # Get logs from last 30 seconds
    docker-compose logs --since=30s --no-color 2>/dev/null | tail -20 | while IFS= read -r line; do
        case "$line" in
            *celery*deploy*)
                echo "🚀 [DEPLOY] $line"
                ;;
            *celery*generate*)
                echo "🤖 [AI-GEN] $line"
                ;;
            *backend*POST*)
                echo "📤 [API-POST] $line"
                ;;
            *backend*GET*)
                echo "📥 [API-GET] $line"
                ;;
            *ERROR*)
                echo "❌ [ERROR] $line"
                ;;
            *SUCCESS*)
                echo "✅ [SUCCESS] $line"
                ;;
            *)
                echo "   $line"
                ;;
        esac
    done
    echo "─────────────────────────────────────────────────────────────────"
}

# Function to show deployment status
show_deployments() {
    echo ""
    echo "🐳 DEPLOYED APPS:"
    deployed=$(docker ps --filter "label=faibric.project_id" --format "table {{.Names}}\t{{.Status}}" 2>/dev/null | tail -n +2)
    if [ -z "$deployed" ]; then
        echo "   No apps currently deployed"
    else
        echo "$deployed"
    fi
    echo ""
}

# Show initial status
show_status
show_deployments

echo "🔄 LIVE LOGS (Updates every 3 seconds, Ctrl+C to stop):"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Tail logs in real-time
docker-compose logs -f --tail=0 2>&1 | while IFS= read -r line; do
    timestamp=$(date '+%H:%M:%S')
    
    case "$line" in
        *"Task apps.deployment.tasks.deploy_app_task"*"received"*)
            echo "[$timestamp] 🚀 DEPLOYMENT STARTED"
            ;;
        *"Task apps.deployment.tasks.deploy_app_task"*"succeeded"*)
            echo "[$timestamp] ✅ DEPLOYMENT COMPLETED"
            ;;
        *"Task apps.ai_engine.tasks.generate_app_task"*"received"*)
            echo "[$timestamp] 🤖 AI GENERATION STARTED"
            ;;
        *"Task apps.ai_engine.tasks.generate_app_task"*"succeeded"*)
            echo "[$timestamp] ✅ AI GENERATION COMPLETED"
            ;;
        *"Building image"*)
            echo "[$timestamp] 🐳 Building Docker image..."
            ;;
        *"Image built successfully"*)
            echo "[$timestamp] ✅ Docker image built"
            ;;
        *"Container created"*)
            echo "[$timestamp] ✅ Container created and started"
            ;;
        *"POST /api/projects/"*"201"*)
            echo "[$timestamp] 📝 New project created"
            ;;
        *"POST"*"/publish/"*"200"*)
            echo "[$timestamp] 🚀 Deploy request received"
            ;;
        *"ERROR"*|*"Error"*|*"error"*)
            echo "[$timestamp] ❌ ERROR: $line"
            ;;
        *"celery"*)
            echo "[$timestamp] 🔄 $line" | cut -c1-120
            ;;
        *"backend"*)
            echo "[$timestamp] 🌐 $line" | cut -c1-120
            ;;
    esac
done

