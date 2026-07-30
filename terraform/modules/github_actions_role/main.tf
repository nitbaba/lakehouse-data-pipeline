data "aws_caller_identity" "current" {}

# References the OIDC provider that ALREADY EXISTS in this account (created
# for an unrelated prior project). AWS allows only one OIDC provider per
# issuer URL per account, so this must be a data source, never an
# aws_iam_openid_connect_provider resource (that would try to create a
# duplicate and fail). Looked up by ARN (not URL) deliberately: URL lookups
# require the account-wide iam:ListOpenIDConnectProviders action; ARN
# lookups only need iam:GetOpenIDConnectProvider on this one resource —
# strictly less privilege for a role that runs this same data lookup on
# every future `terraform plan`.
data "aws_iam_openid_connect_provider" "github_actions" {
  arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
}

# Trust policy: only this repo, only on pushes/dispatches from the given
# branch. GitHub's OIDC "sub" claim encodes the ref the workflow ran from
# regardless of whether the event was `push` or `workflow_dispatch`, so no
# separate condition is needed for both triggers. Pull-request events are
# never in scope, and fork PRs never carry a token minted with this repo's
# identity at all, so this can't be reached from untrusted fork PRs.
#
# The owner/repo segments are matched with a "@<numeric-id>" wildcard suffix
# rather than plain names: confirmed via CloudTrail that this account's
# actual sub claims are "repo:nitbaba@66657625/lakehouse-data-pipeline@1316444705:ref:...",
# not the plain "repo:owner/repo:ref:..." the basic OIDC docs describe.
# GitHub appends the owner/repo's immutable database ID this way once an
# account or repo has been renamed, to stop someone else reusing the old
# name to spoof a stale trust policy. Wildcarding the ID (rather than
# hardcoding the current one) keeps this working if that ID context ever
# changes, while still requiring an exact owner/repo name match.
data "aws_iam_policy_document" "trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github_actions.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${split("/", var.github_repo)[0]}@*/${split("/", var.github_repo)[1]}@*:ref:refs/heads/${var.github_branch}"]
    }
  }
}

resource "aws_iam_role" "github_actions_ci" {
  name               = "${var.project_name}-${var.environment}-gh-actions-ci"
  assume_role_policy = data.aws_iam_policy_document.trust.json
}

# Read-only: exactly what `terraform plan`/`init` need to describe this
# repo's own managed resources (s3_bucket + iam_pipeline_role modules) plus
# this role's own resources (self-referential — a future plan run, assumed
# as this role, must be able to read its own role/policy too). No
# write/create/delete actions anywhere — this role can never mutate infra.
data "aws_iam_policy_document" "plan_read_only" {
  statement {
    effect = "Allow"
    actions = [
      "s3:GetBucketVersioning",
      "s3:GetBucketPublicAccessBlock",
      "s3:GetBucketOwnershipControls",
      "s3:GetEncryptionConfiguration",
      "s3:GetLifecycleConfiguration",
      "s3:GetBucketTagging",
      "s3:GetBucketLocation",
      "s3:GetBucketAcl",
      "s3:ListBucket",
    ]
    resources = [var.bucket_arn]
  }

  statement {
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${var.bucket_arn}/*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "iam:GetRole",
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:ListRolePolicies",
      "iam:ListAttachedRolePolicies",
      "iam:ListRoleTags",
      "iam:ListPolicyTags",
    ]
    resources = [
      var.pipeline_role_arn,
      var.pipeline_policy_arn,
      aws_iam_role.github_actions_ci.arn,
      # Not aws_iam_policy.plan_read_only.arn: that resource is created FROM
      # this document, so referencing it back here is a real dependency
      # cycle (confirmed via `terraform validate`). Construct the ARN
      # directly instead — it's fully deterministic from the same name this
      # module gives the policy resource below.
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/${var.project_name}-${var.environment}-gh-actions-ci-plan-read-only",
    ]
  }

  statement {
    effect    = "Allow"
    actions   = ["iam:GetOpenIDConnectProvider"]
    resources = [data.aws_iam_openid_connect_provider.github_actions.arn]
  }

  statement {
    effect    = "Allow"
    actions   = ["sts:GetCallerIdentity"]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "plan_read_only" {
  name   = "${var.project_name}-${var.environment}-gh-actions-ci-plan-read-only"
  policy = data.aws_iam_policy_document.plan_read_only.json
}

resource "aws_iam_role_policy_attachment" "plan_read_only" {
  role       = aws_iam_role.github_actions_ci.name
  policy_arn = aws_iam_policy.plan_read_only.arn
}
