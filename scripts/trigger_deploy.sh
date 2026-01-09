#!/bin/bash
# Trigger a deploy on Render.com for faibric-api
#
# Usage:
#   Option 1: With API key
#     RENDER_API_KEY=your_key ./trigger_deploy.sh
#
#   Option 2: With deploy hook (get from Render dashboard)
#     ./trigger_deploy.sh https://api.render.com/deploy/srv-xxx?key=yyy

if [ -n "$1" ]; then
    # Deploy hook URL provided
    echo "Triggering deploy via hook..."
    curl -X GET "$1"
elif [ -n "$RENDER_API_KEY" ]; then
    # Use API key to find service and deploy
    echo "Finding faibric-api service..."

    SERVICE_ID=$(curl -s "https://api.render.com/v1/services?name=faibric-api&limit=1" \
        -H "Authorization: Bearer $RENDER_API_KEY" \
        | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

    if [ -z "$SERVICE_ID" ]; then
        echo "Could not find faibric-api service"
        exit 1
    fi

    echo "Found service: $SERVICE_ID"
    echo "Triggering deploy..."

    curl -X POST "https://api.render.com/v1/services/$SERVICE_ID/deploys" \
        -H "Authorization: Bearer $RENDER_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"clearCache": "do_not_clear"}'

    echo ""
    echo "Deploy triggered! Check status at:"
    echo "https://dashboard.render.com/web/$SERVICE_ID"
else
    echo "Usage:"
    echo "  RENDER_API_KEY=your_key ./trigger_deploy.sh"
    echo "  OR"
    echo "  ./trigger_deploy.sh DEPLOY_HOOK_URL"
    echo ""
    echo "Get API key from: https://dashboard.render.com/u/settings#api-keys"
    echo "Get deploy hook from: Render Dashboard > faibric-api > Settings > Deploy Hook"
fi
