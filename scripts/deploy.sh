#!/usr/bin/env bash
# ============================================================
# Mission Control — One-Command Deploy
# Run this FROM YOUR MAC to deploy to the Azure VM
#
# Usage:
#   ./scripts/deploy.sh
#   MC_ANTHROPIC_API_KEY=sk-ant-... ./scripts/deploy.sh
# ============================================================
set -euo pipefail

VM_IP="20.119.62.230"
VM_USER="azureuser"
SSH_KEY="$HOME/.ssh/id_rsa"
API_KEY="${MC_ANTHROPIC_API_KEY:-}"

echo "=========================================="
echo "  Mission Control — Deploy to Azure VM"
echo "=========================================="
echo "  VM: $VM_USER@$VM_IP"
echo ""

# Check SSH key
if [ ! -f "$SSH_KEY" ]; then
    echo "ERROR: SSH key not found at $SSH_KEY"
    echo "Set SSH_KEY env var or use: SSH_KEY=/path/to/key ./scripts/deploy.sh"
    exit 1
fi

SSH_CMD="ssh -o StrictHostKeyChecking=no -i $SSH_KEY $VM_USER@$VM_IP"

# Step 1: Test connection
echo "[Step 1] Testing SSH connection..."
$SSH_CMD "echo 'SSH OK'" || { echo "ERROR: Cannot connect to VM"; exit 1; }

# Step 2: Upload setup script
echo "[Step 2] Uploading setup script..."
scp -o StrictHostKeyChecking=no -i "$SSH_KEY" \
    "$(dirname "$0")/server_setup.sh" \
    "$VM_USER@$VM_IP:/tmp/server_setup.sh"

# Step 3: Run setup on VM
echo "[Step 3] Running setup on VM (this takes 2-3 minutes)..."
$SSH_CMD "chmod +x /tmp/server_setup.sh && MC_ANTHROPIC_API_KEY='$API_KEY' bash /tmp/server_setup.sh"

# Step 4: Upload and run smoke test
echo ""
echo "[Step 4] Running smoke test..."
scp -o StrictHostKeyChecking=no -i "$SSH_KEY" \
    "$(dirname "$0")/live_smoke_test.sh" \
    "$VM_USER@$VM_IP:/tmp/live_smoke_test.sh"
$SSH_CMD "chmod +x /tmp/live_smoke_test.sh && bash /tmp/live_smoke_test.sh"

echo ""
echo "=========================================="
echo "  DEPLOYMENT SUCCESSFUL"
echo "=========================================="
echo ""
echo "  Dashboard:  http://$VM_IP"
echo "  API:        http://$VM_IP/api/health"
echo "  API Docs:   http://$VM_IP/api/docs"
echo "  Backend:    http://$VM_IP:8000"
echo ""
echo "  SSH:        ssh -i $SSH_KEY $VM_USER@$VM_IP"
echo ""
echo "  Manage:"
echo "    sudo systemctl status mc-backend"
echo "    sudo systemctl restart mc-backend"
echo "    sudo journalctl -u mc-backend -f"
echo ""
