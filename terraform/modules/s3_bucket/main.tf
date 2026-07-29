# force_destroy = true is a dev-only convenience so `terraform destroy` cleans up
# freely during iteration. Never set this on a production data lake bucket.
resource "aws_s3_bucket" "this" {
  bucket        = var.bucket_name
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  bucket = aws_s3_bucket.this.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# Only expire noncurrent versions. No rules touch current objects — Iceberg
# snapshots reference data files by exact key and must never expire out from
# under a live table.
resource "aws_s3_bucket_lifecycle_configuration" "this" {
  bucket = aws_s3_bucket.this.id

  rule {
    id     = "expire-noncurrent-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = var.noncurrent_version_expiration_days
    }
  }
}

# Pre-create the landing and warehouse prefixes so later phases (dlt ingestion,
# Iceberg REST catalog) have somewhere to write without any ingestion logic here.
resource "aws_s3_object" "landing_marker" {
  bucket  = aws_s3_bucket.this.id
  key     = "landing/.keep"
  content = ""
}

resource "aws_s3_object" "warehouse_marker" {
  bucket  = aws_s3_bucket.this.id
  key     = "warehouse/.keep"
  content = ""
}
