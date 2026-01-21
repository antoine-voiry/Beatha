#!/bin/bash
# Push to Pi - Rapid Development Deployment
# Usage: ./scripts/push_to_pi.sh [USER@]HOST
# Example: ./scripts/push_to_pi.sh pi@beatha.local

DESTINATION=$1

if [ -z "$DESTINATION" ]; then
    echo "❌ Error: Missing destination."
    echo "Usage: $0 [USER@]HOST"
    echo "Example: $0 pi@beatha.local"
    exit 1
fi

REMOTE_DIR="~/beatha-project"

echo "🚀 Deploying to $DESTINATION..."

# 1. Sync Files (RSYNC)
# Excludes heavy/local folders that shouldn't be synced
rsync -avz --progress \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '.DS_Store' \
    --exclude 'node_modules' \
    --exclude 'tmp' \
    ./ "$DESTINATION:$REMOTE_DIR"

if [ $? -eq 0 ]; then
    echo "✅ File Sync Complete."

    # 2. Remote Restart
    echo "🔄 Restarting Service..."
    ssh "$DESTINATION" "sudo systemctl restart beatha"

    echo "🎉 Deployed & Restarted!"
    echo "   Logs: ssh $DESTINATION 'tail -f /var/log/beatha.log'"
else
    echo "❌ Sync Failed. Check connection to $DESTINATION"
fi
