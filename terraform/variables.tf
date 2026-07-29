variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short project name used as a resource name prefix"
  type        = string
  default     = "lakehouse"
}

variable "environment" {
  description = "Deployment environment (e.g. dev, prod)"
  type        = string
  default     = "dev"
}

variable "noncurrent_version_expiration_days" {
  description = "Days after which noncurrent S3 object versions are expired"
  type        = number
  default     = 30
}
