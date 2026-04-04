#!/usr/bin/env bash
###############################################################################
# setup_server.sh
# Run ONCE after SSHing into the EC2 instance.
# Usage:  bash setup_server.sh
###############################################################################
set -e

APP_DIR="/opt/chatbot"
REPO_URL="https://github.com/YOUR_USERNAME/YOUR_REPO.git"  # ← change this

echo "──────────────────────────────────────────"
echo "  AI Chatbot — Server Setup"
echo "──────────────────────────────────────────"

# 1. System packages
echo "[1/7] Installing system packages..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git curl

# 2. Create app user (if not exists)
echo "[2/7] Creating app user..."
id -u appuser &>/dev/null || sudo useradd -m -s /bin/bash appuser

# 3. Clone repo
echo "[3/7] Cloning repository..."
sudo mkdir -p "$APP_DIR"
sudo chown appuser:appuser "$APP_DIR"

if [ -d "$APP_DIR/.git" ]; then
    echo "  Repo already cloned, pulling latest..."
    cd "$APP_DIR" && sudo -u appuser git pull origin main
else
    sudo -u appuser git clone "$REPO_URL" "$APP_DIR"
fi

# 4. Python virtual environment
echo "[4/7] Setting up Python venv..."
cd "$APP_DIR"
sudo -u appuser python3 -m venv venv
sudo -u appuser ./venv/bin/pip install --upgrade pip --quiet
sudo -u appuser ./venv/bin/pip install -r requirements.txt --quiet

# 5. .env file (interactive)
echo "[5/7] Configuring environment variables..."
if [ ! -f "$APP_DIR/.env" ]; then
    sudo tee "$APP_DIR/.env" > /dev/null <<'EOF'
GROQ_API_KEY=
S3_BUCKET=
AWS_REGION=ap-south-1
EMAIL_USER=
EMAIL_PASS=
EOF
fi

echo ""
echo "  ⚠️  Please edit /opt/chatbot/.env with your real values:"
echo "      sudo nano /opt/chatbot/.env"
echo ""

# 6. systemd service
echo "[6/7] Installing systemd service..."
sudo cp "$APP_DIR/chatbot.service" /etc/systemd/system/chatbot.service
sudo chmod 644 /etc/systemd/system/chatbot.service

# Allow appuser to restart the service without sudo password
echo "appuser ALL=(ALL) NOPASSWD: /bin/systemctl restart chatbot, /bin/systemctl status chatbot, /bin/systemctl is-active chatbot" \
    | sudo tee /etc/sudoers.d/chatbot > /dev/null

# Allow ubuntu user (CI/CD) to restart the service
echo "ubuntu ALL=(ALL) NOPASSWD: /bin/systemctl restart chatbot, /bin/systemctl status chatbot, /bin/systemctl is-active chatbot" \
    | sudo tee -a /etc/sudoers.d/chatbot > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable chatbot
sudo systemctl start chatbot

# 7. Done
echo "[7/7] Setup complete!"
echo ""
echo "──────────────────────────────────────────"
echo "  Next steps:"
echo ""
echo "  1. Fill in secrets:  sudo nano /opt/chatbot/.env"
echo "  2. Restart service:  sudo systemctl restart chatbot"
echo "  3. Check status:     sudo systemctl status chatbot"
echo "  4. View logs:        sudo journalctl -u chatbot -f"
echo ""
echo "  App URL: http://$(curl -s ifconfig.me):8501"
echo "──────────────────────────────────────────"
