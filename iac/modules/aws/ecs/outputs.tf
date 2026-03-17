output "service_task_roles" {
  description = "Map of service names to their task role ARNs"
  value = {
    for svc_name in keys(var.services) : svc_name => aws_iam_role.task_role.arn
  }
}

output "cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.cluster.name
}

output "cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.cluster.arn
}

output "efs_file_system_ids" {
  description = "Map of EFS file system IDs"
  value = {
    for k, v in aws_efs_file_system.service_volumes : k => v.id
  }
}
