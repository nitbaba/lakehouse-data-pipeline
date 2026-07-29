# Assumable role instead of a new long-lived access key: nothing secret ends up
# in local tfstate, and containers pick up credentials via the AWS SDK's
# AssumeRole credential chain (see ~/.aws/config profile setup in README.md).
data "aws_iam_policy_document" "trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = [var.trusted_principal_arn]
    }
  }
}

resource "aws_iam_role" "lakehouse_pipeline" {
  name               = "${var.project_name}-${var.environment}-pipeline"
  assume_role_policy = data.aws_iam_policy_document.trust.json
}

# Least privilege: list + read/write/delete objects, scoped to this bucket only.
data "aws_iam_policy_document" "s3_access" {
  statement {
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [var.bucket_arn]
  }

  statement {
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = ["${var.bucket_arn}/*"]
  }
}

resource "aws_iam_policy" "s3_access" {
  name   = "${var.project_name}-${var.environment}-pipeline-s3-access"
  policy = data.aws_iam_policy_document.s3_access.json
}

resource "aws_iam_role_policy_attachment" "s3_access" {
  role       = aws_iam_role.lakehouse_pipeline.name
  policy_arn = aws_iam_policy.s3_access.arn
}
