variable "s3_workspace_bucket_arn" {
  description = "ARN of the S3 bucket for workspace archival"
  type        = string
  default     = ""
}

variable "s3_workspace_bucket_name" {
  description = "Name of the S3 bucket for workspace archival"
  type        = string
  default     = ""
}
