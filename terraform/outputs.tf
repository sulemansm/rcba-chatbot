###############################################################################
# outputs.tf
###############################################################################

output "ec2_public_ip" {
  description = "Public IP of the EC2 instance"
  value       = aws_instance.chatbot.public_ip
}

output "ec2_public_dns" {
  description = "Public DNS of the EC2 instance"
  value       = aws_instance.chatbot.public_dns
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket storing leads"
  value       = aws_s3_bucket.leads.bucket
}

output "app_url" {
  description = "Direct Streamlit app URL"
  value       = "http://${aws_instance.chatbot.public_ip}:8501"
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ~/.ssh/${var.key_pair_name}.pem ubuntu@${aws_instance.chatbot.public_ip}"
}
