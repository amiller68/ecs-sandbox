# Container configuration defaults for all services
output "container" {
  description = "Default container configuration"
  value = {
    port       = 8000
    cpu        = 256
    memory     = 512
    repository = var.name
    tag        = var.environment == "production" ? "latest" : "staging-latest"
    health_check = "/health"
    environment = [
      {
        name  = "ENV"
        value = var.environment
      }
    ]
  }
}

# Service configuration defaults for all services
output "service" {
  description = "Default service configuration"
  value = {
    description           = "${var.name} service"
    desired_count         = 1
    auto_scaling          = true
    min_capacity          = 1
    max_capacity          = 3
    scaling_cpu_threshold = 70
    lb_listener_rule = {
      path_pattern = ["/${var.name}/*"]
    }
  }
}
