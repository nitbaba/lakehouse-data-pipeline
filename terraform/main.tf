data "aws_caller_identity" "current" {}

locals {
  bucket_name = "${var.project_name}-${var.environment}-${data.aws_caller_identity.current.account_id}"
}

module "lakehouse_bucket" {
  source = "./modules/s3_bucket"

  bucket_name                        = local.bucket_name
  noncurrent_version_expiration_days = var.noncurrent_version_expiration_days
}

module "lakehouse_iam" {
  source = "./modules/iam_pipeline_role"

  bucket_arn            = module.lakehouse_bucket.bucket_arn
  trusted_principal_arn = data.aws_caller_identity.current.arn
  project_name          = var.project_name
  environment           = var.environment
}

module "github_actions_ci" {
  source = "./modules/github_actions_role"

  project_name        = var.project_name
  environment         = var.environment
  github_repo         = var.github_repo
  github_branch       = var.github_branch
  bucket_arn          = module.lakehouse_bucket.bucket_arn
  pipeline_role_arn   = module.lakehouse_iam.role_arn
  pipeline_policy_arn = module.lakehouse_iam.policy_arn
}
