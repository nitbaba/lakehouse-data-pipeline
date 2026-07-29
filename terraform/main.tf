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
