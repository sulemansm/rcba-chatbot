###############################################################################
# main.tf  —  AI Chatbot AWS Infrastructure
# Region: ap-south-1 (Mumbai)  |  Free-tier eligible
###############################################################################

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ── Data: Latest Ubuntu 22.04 LTS AMI ─────────────────────────────────────────
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]  # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ── S3 Bucket ──────────────────────────────────────────────────────────────────
resource "aws_s3_bucket" "leads" {
  bucket        = var.s3_bucket_name
  force_destroy = true

  tags = {
    Name        = "chatbot-leads"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "leads" {
  bucket = aws_s3_bucket.leads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "leads" {
  bucket = aws_s3_bucket.leads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ── IAM Role for EC2 ───────────────────────────────────────────────────────────
resource "aws_iam_role" "chatbot_ec2" {
  name = "chatbot-ec2-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })

  tags = { Name = "chatbot-ec2-role" }
}

resource "aws_iam_role_policy" "s3_access" {
  name = "chatbot-s3-policy"
  role = aws_iam_role.chatbot_ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.leads.arn,
          "${aws_s3_bucket.leads.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_instance_profile" "chatbot_ec2" {
  name = "chatbot-ec2-profile-${var.environment}"
  role = aws_iam_role.chatbot_ec2.name
}

# ── Security Group ─────────────────────────────────────────────────────────────
resource "aws_security_group" "chatbot" {
  name        = "chatbot-sg-${var.environment}"
  description = "Chatbot app security group"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Streamlit"
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "chatbot-sg" }
}

# ── EC2 Instance ───────────────────────────────────────────────────────────────
resource "aws_instance" "chatbot" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.chatbot.id]
  iam_instance_profile   = aws_iam_instance_profile.chatbot_ec2.name

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  # Bootstrap: install dependencies and prepare app directory
  user_data = <<-EOF
    #!/bin/bash
    set -e

    apt-get update -y
    apt-get install -y python3 python3-pip python3-venv git curl

    # Create app user
    useradd -m -s /bin/bash appuser

    # Create app directory
    mkdir -p /opt/chatbot
    chown appuser:appuser /opt/chatbot

    # Create .env template (fill in after SSH)
    cat > /opt/chatbot/.env <<'ENVEOF'
    GROQ_API_KEY=your_groq_api_key_here
    S3_BUCKET=${var.s3_bucket_name}
    AWS_REGION=${var.aws_region}
    EMAIL_USER=your_gmail@gmail.com
    EMAIL_PASS=your_gmail_app_password
    ENVEOF

    chown appuser:appuser /opt/chatbot/.env
    chmod 600 /opt/chatbot/.env

    echo "Bootstrap complete." >> /var/log/chatbot-bootstrap.log
  EOF

  tags = {
    Name        = "chatbot-server"
    Environment = var.environment
  }
}
