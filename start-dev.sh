#!/bin/bash
# Faibric Development Environment with Monitoring
# Starts backend, frontend, and monitoring service

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Faibric Development Environment${NC}"
echo -e "${GREEN}========================================${NC}"

# Alert email (can be overridden)
ALERT_EMAIL="${ALERT_EMAIL:-abram@faibric.com}"

# Kill any existing processes
echo -e "${YELLOW}Cleaning up existing processes...${NC}"
pkill -9 -f "manage.py runserver" 2>/dev/null || true
pkill -9 -f "vite" 2>/dev/null || true
pkill -9 -f "monitor_services.py" 2>/dev/null || true
sleep 2

# Load environment
if [ -f "$PROJECT_ROOT/.env.local" ]; then
    echo -e "${GREEN}Loading .env.local...${NC}"
    export $(grep -v '^#' "$PROJECT_ROOT/.env.local" | xargs)
fi

# Start backend
echo -e "${YELLOW}Starting backend...${NC}"
cd "$PROJECT_ROOT/backend"
python manage.py runserver 0.0.0.0:8000 > /tmp/django.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}Backend PID: $BACKEND_PID${NC}"

# Wait for backend
sleep 3
if curl -s http://localhost:8000/api/health/ > /dev/null; then
    echo -e "${GREEN}Backend started successfully${NC}"
else
    echo -e "${RED}Backend failed to start! Check /tmp/django.log${NC}"
    tail -20 /tmp/django.log
    exit 1
fi

# Start frontend
echo -e "${YELLOW}Starting frontend...${NC}"
cd "$PROJECT_ROOT/frontend"
npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}Frontend PID: $FRONTEND_PID${NC}"

# Wait for frontend
sleep 4
if curl -s http://localhost:5173/ > /dev/null; then
    echo -e "${GREEN}Frontend started successfully${NC}"
else
    echo -e "${RED}Frontend failed to start! Check /tmp/frontend.log${NC}"
    tail -20 /tmp/frontend.log
    exit 1
fi

# Start monitor
echo -e "${YELLOW}Starting service monitor...${NC}"
cd "$PROJECT_ROOT"
python monitor_services.py "$ALERT_EMAIL" > /tmp/monitor.log 2>&1 &
MONITOR_PID=$!
echo -e "${GREEN}Monitor PID: $MONITOR_PID${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   All services running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "  Frontend:  ${GREEN}http://localhost:5173${NC}"
echo -e "  Backend:   ${GREEN}http://localhost:8000${NC}"
echo -e "  Alerts to: ${GREEN}$ALERT_EMAIL${NC}"
echo ""
echo -e "${YELLOW}Logs:${NC}"
echo "  Backend:  /tmp/django.log"
echo "  Frontend: /tmp/frontend.log"
echo "  Monitor:  /tmp/monitor.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Save PIDs for cleanup
echo "$BACKEND_PID $FRONTEND_PID $MONITOR_PID" > /tmp/faibric_pids.txt

# Wait and handle Ctrl+C
cleanup() {
    echo -e "\n${YELLOW}Stopping all services...${NC}"
    kill $BACKEND_PID $FRONTEND_PID $MONITOR_PID 2>/dev/null || true
    rm -f /tmp/faibric_pids.txt
    echo -e "${GREEN}Stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Keep running
wait
