output "load_balancer_dns" {
  description = "DNS name of the load balancer"
  value       = module.loadbalancer.dns_name
}

output "service_urls" {
  description = "Map of service names to their public URLs"
  value = {
    for service_name, service_config in module.services.services :
    service_name => "https://${module.loadbalancer.dns_name}/${service_name}"
    if service_config.lb_listener_rule != null
  }
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = module.services_ecs.cluster_name
}

output "efs_file_system_ids" {
  description = "Map of EFS file system IDs"
  value       = module.services_ecs.efs_file_system_ids
}

output "s3_workspace_bucket" {
  description = "S3 bucket name for workspace archival (empty if disabled)"
  value       = var.enable_s3_archival ? aws_s3_bucket.workspaces[0].bucket : ""
}
