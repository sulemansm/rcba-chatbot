# ⚡ AI Chatbot — Production Deployment Guide

A production-ready Streamlit chatbot powered by **Groq (LLaMA 3)**, deployed on **AWS EC2**, with **S3** lead storage and **Gmail** email notifications.

---

## 📁 Project Structure

```
chatbot-app/
├── app.py                          # Main Streamlit UI
├── ai_service.py                   # Groq API integration
├── s3_service.py                   # AWS S3 lead storage
├── email_service.py                # Gmail SMTP notifications
├── requirements.txt                # Python dependencies
├── chatbot.service                 # systemd service definition
├── setup_server.sh                 # One-time server setup script
├── Caddyfile                       # Optional HTTPS reverse proxy
├── .streamlit/
│   └── config.toml                 # Streamlit configuration
├── terraform/
│   ├── main.tf                     # EC2, S3, IAM, Security Group
│   ├── variables.tf                # Input variables
│   ├── outputs.tf                  # EC2 IP, S3 name, app URL
│   └── terraform.tfvars.example    # Example variable values
└── .github/
    └── workflows/
        └── deploy.yml              # CI/CD pipeline
```

---

## 🔑 Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Terraform | ≥ 1.5 | Infrastructure provisioning |
| AWS CLI | ≥ 2.x | AWS credentials |
| Python | 3.10+ | Local development |
| Git | any | Version control |

---

## 🚀 Step-by-Step Deployment

### Step 1 — Get API Keys

#### Groq API Key
1. Visit [console.groq.com](https://console.groq.com)
2. Sign up / log in → **API Keys** → **Create API Key**
3. Copy the key (shown only once)

#### Gmail App Password (for EMAIL_PASS)
1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** (required)
3. Search **"App Passwords"** → Create for **Mail / Other**
4. Copy the 16-character password (no spaces needed)

---

### Step 2 — AWS Setup

#### Configure AWS CLI
```bash
aws configure
# AWS Access Key ID:     [your key]
# AWS Secret Access Key: [your secret]
# Default region:        ap-south-1
# Default output format: json
```

#### Create EC2 Key Pair (if you don't have one)
```bash
aws ec2 create-key-pair \
    --key-name chatbot-key \
    --region ap-south-1 \
    --query 'KeyMaterial' \
    --output text > ~/.ssh/chatbot-key.pem

chmod 400 ~/.ssh/chatbot-key.pem
```

---

### Step 3 — Provision Infrastructure with Terraform

```bash
cd terraform

# Copy and edit the vars file
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars
```

Fill in `terraform.tfvars`:
```hcl
aws_region       = "ap-south-1"
environment      = "production"
instance_type    = "t2.micro"
key_pair_name    = "chatbot-key"          # name you created above
s3_bucket_name   = "my-chatbot-leads-2024"  # must be globally unique
allowed_ssh_cidr = "0.0.0.0/0"
```

```bash
terraform init
terraform plan
terraform apply   # type "yes" when prompted
```

Note the outputs:
```
ec2_public_ip = "13.x.x.x"
app_url       = "http://13.x.x.x:8501"
ssh_command   = "ssh -i ~/.ssh/chatbot-key.pem ubuntu@13.x.x.x"
s3_bucket_name = "my-chatbot-leads-2024"
```

---

### Step 4 — Deploy Application on EC2

#### 4a. SSH into the server
```bash
ssh -i ~/.ssh/chatbot-key.pem ubuntu@<EC2_PUBLIC_IP>
```

#### 4b. Clone your repository
```bash
# On the EC2 instance:
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git /opt/chatbot
cd /opt/chatbot
```

#### 4c. Run the setup script
```bash
bash setup_server.sh
```

This will:
- Install Python, Git, and dependencies
- Create a Python virtual environment
- Install all pip packages
- Set up the systemd service
- Start the app

#### 4d. Fill in your secrets
```bash
sudo nano /opt/chatbot/.env
```

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
S3_BUCKET=my-chatbot-leads-2024
AWS_REGION=ap-south-1
EMAIL_USER=your.email@gmail.com
EMAIL_PASS=abcd efgh ijkl mnop
```

```bash
# Restart to apply new env vars
sudo systemctl restart chatbot
sudo systemctl status chatbot
```

---

### Step 5 — Access the App

Open your browser:
```
http://<EC2_PUBLIC_IP>:8501
```

You should see the AI chatbot interface. 🎉

---

### Step 6 — Set Up CI/CD (GitHub Actions)

#### Add GitHub Secrets
Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Value |
|-------------|-------|
| `EC2_HOST` | Your EC2 public IP (e.g. `13.x.x.x`) |
| `EC2_SSH_KEY` | Content of `~/.ssh/chatbot-key.pem` (full file) |

#### How to copy your PEM key content
```bash
cat ~/.ssh/chatbot-key.pem
# Copy the full output including -----BEGIN RSA PRIVATE KEY----- headers
```

#### Test CI/CD
Push any change to `main` branch → GitHub Actions will auto-deploy.

---

## 🔧 Useful Commands

```bash
# Check app status
sudo systemctl status chatbot

# View live logs
sudo journalctl -u chatbot -f

# Restart app
sudo systemctl restart chatbot

# Stop app
sudo systemctl stop chatbot

# View leads in S3
aws s3 ls s3://YOUR_BUCKET_NAME/leads/ --region ap-south-1
```

---

## 🌐 Optional: HTTPS with Custom Domain (Caddy)

If you have a custom domain:

1. Point your domain's A record → EC2 IP
2. Install Caddy on EC2:
```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```

3. Edit `Caddyfile` with your domain
4. Start Caddy:
```bash
sudo cp /opt/chatbot/Caddyfile /etc/caddy/Caddyfile
sudo systemctl restart caddy
```

Access via `https://chat.yourdomain.com`

---

## 🔐 Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ | Groq console API key |
| `S3_BUCKET` | ✅ | S3 bucket name for lead storage |
| `AWS_REGION` | ✅ | AWS region (e.g. `ap-south-1`) |
| `EMAIL_USER` | ✅ | Gmail address |
| `EMAIL_PASS` | ✅ | Gmail App Password (16 chars) |

---

## 💰 Cost Estimate (AWS Free Tier)

| Resource | Free Tier | Cost After |
|----------|-----------|------------|
| EC2 t2.micro | 750 hrs/month free (12 months) | ~$8/month |
| S3 | 5 GB + 20k requests free | < $0.05/month |
| Data transfer | 15 GB free | Minimal |

**Total estimated cost: $0 for first year on free tier**

---

## 🐛 Troubleshooting

**App not accessible on port 8501**
→ Check Security Group allows TCP 8501 from 0.0.0.0/0

**Service not starting**
```bash
sudo journalctl -u chatbot -n 50 --no-pager
```

**S3 access denied**
→ Ensure EC2 IAM Role has S3 permissions and is attached to the instance

**Email not sending**
→ Verify Gmail 2FA is on, App Password is correct, no spaces in `.env` value

**Groq API errors**
→ Check GROQ_API_KEY is set; verify at console.groq.com
