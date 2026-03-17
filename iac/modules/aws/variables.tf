variable "environment" {
  description = "Environment name"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be one of: staging, production"
  }
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "enable_s3_archival" {
  description = "Enable S3 bucket for workspace archival"
  type        = bool
  default     = false
}

# Optional per-environment service configuration overrides
variable "service_configurations" {
  description = "Optional per-environment service configuration overrides"
  type = map(object({
    container = optional(object({
      cpu    = optional(number)
      memory = optional(number)
      environment = optional(list(object({
        name  = string
        value = string
      })))
    }))

    desired_count = optional(number)
    auto_scaling = optional(object({
      enabled       = optional(bool)
      min_capacity  = optional(number)
      max_capacity  = optional(number)
      cpu_threshold = optional(number)
    }))
  }))
  default = {}
}
