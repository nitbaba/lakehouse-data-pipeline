output "bucket_id" {
  description = "Name of the lakehouse S3 bucket"
  value       = module.lakehouse_bucket.bucket_id
}

output "bucket_arn" {
  description = "ARN of the lakehouse S3 bucket"
  value       = module.lakehouse_bucket.bucket_arn
}

output "iam_role_arn" {
  description = "ARN of the assumable pipeline IAM role — use as role_arn in ~/.aws/config"
  value       = module.lakehouse_iam.role_arn
}
