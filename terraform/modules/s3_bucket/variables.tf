variable "bucket_name" {
  description = "Globally-unique S3 bucket name"
  type        = string
}

variable "noncurrent_version_expiration_days" {
  description = "Days after which noncurrent object versions are expired"
  type        = number
}
