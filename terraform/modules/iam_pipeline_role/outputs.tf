output "role_arn" {
  value = aws_iam_role.lakehouse_pipeline.arn
}

output "policy_arn" {
  value = aws_iam_policy.s3_access.arn
}
