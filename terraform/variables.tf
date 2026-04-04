###############################################################################
# variables.tf
###############################################################################

variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Deployment environment tag"
  type        = string
  default     = "production"
}

variable "instance_type" {
  description = "EC2 instance type (t2.micro = free tier)"
  type        = string
  default     = "t2.micro"
}

variable "key_pair_name" {
  description = "Name of an existing EC2 Key Pair for SSH access"
  type        = string
  # Set via: terraform apply -var="key_pair_name=my-key"
  # or create a terraform.tfvars file
}

variable "s3_bucket_name" {
  description = "Globally unique S3 bucket name for lead storage"
  type        = string
  # Example: "my-chatbot-leads-2024"
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH into the instance (restrict in production)"
  type        = string
  default     = "0.0.0.0/0"   # Change to your IP: "203.0.113.0/32"
}
