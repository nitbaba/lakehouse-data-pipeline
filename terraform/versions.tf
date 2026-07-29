terraform {
  required_version = ">= 1.15"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # No backend block: state is kept locally (terraform/terraform.tfstate, gitignored).
  # This is a deliberate choice for a single-operator portfolio project — a remote
  # backend with state locking would be the production upgrade.
}
