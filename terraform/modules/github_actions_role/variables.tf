variable "project_name" {
  description = "Short project name used as a resource name prefix"
  type        = string
}

variable "environment" {
  description = "Deployment environment (e.g. dev, prod)"
  type        = string
}

variable "github_repo" {
  description = "GitHub repo in \"owner/name\" form allowed to assume this role"
  type        = string
}

variable "github_branch" {
  description = "Branch ref this role's trust policy is scoped to"
  type        = string
  default     = "master"
}

variable "bucket_arn" {
  description = "ARN of the lakehouse S3 bucket"
  type        = string
}

variable "pipeline_role_arn" {
  description = "ARN of the lakehouse pipeline IAM role"
  type        = string
}

variable "pipeline_policy_arn" {
  description = "ARN of the lakehouse pipeline IAM policy"
  type        = string
}
