output "load_balancer_dns" {
  value = module.common.load_balancer_dns
}

output "service_urls" {
  value = module.common.service_urls
}

output "ecs_cluster_name" {
  value = module.common.ecs_cluster_name
}
