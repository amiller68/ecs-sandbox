output "load_balancer_dns" {
  description = "DNS name of the load balancer"
  value       = var.aws_config != null ? module.aws[0].load_balancer_dns : ""
}

output "service_urls" {
  description = "Map of service names to their public URLs"
  value       = var.aws_config != null ? module.aws[0].service_urls : {}
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = var.aws_config != null ? module.aws[0].ecs_cluster_name : ""
}
