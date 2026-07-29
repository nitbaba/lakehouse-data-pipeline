variable "bucket_arn" {
  description = "ARN of the lakehouse S3 bucket to grant access to"
  type        = string
}

variable "trusted_principal_arn" {
  description = "ARN of the IAM principal allowed to assume this role"
  type        = string
}

variable "project_name" {
  description = "Short project name used as a resource name prefix"
  type        = string
}

variable "environment" {
  description = "Deployment environment (e.g. dev, prod)"
  type        = string
}
