variable "environment" {
  description = "Environment name"
  type        = string
}

variable "hosted_zone_dns_name" {
  description = "The DNS name of the hosted zone (e.g. aws.krondor.org)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs"
  type        = list(string)
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "route53_zone_id" {
  description = "Route53 hosted zone ID"
  type        = string
}
