# ECS Module
# Creates cluster, task definitions, services, auto-scaling, EFS, and EventBridge cron

# -------------------------------------------------------
# Data sources
# -------------------------------------------------------

data "aws_ecr_repository" "repos" {
  for_each = {
    for name, svc in var.services : svc.container.repository => svc
  }
  name = each.key
}

data "aws_caller_identity" "current" {}

# -------------------------------------------------------
# Locals
# -------------------------------------------------------

locals {
  # Services that have EFS volumes
  services_with_volumes = flatten([
    for name, svc in var.services : [
      for volume in coalesce(lookup(svc, "volumes", []), []) : {
        service_name = name
        volume_name  = volume.name
        efs_config   = lookup(volume, "efs", null)
      }
      if lookup(volume, "efs", null) != null
    ]
  ])

  # Flat map of all EFS volume configs keyed by "service-volume"
  efs_volume_map = {
    for pair in flatten([
      for name, svc in var.services : [
        for volume in coalesce(lookup(svc, "volumes", []), []) : {
          key = "${name}-${volume.name}"
          value = merge(
            {
              service_name = name
              volume_name  = volume.name
            },
            lookup(volume, "efs", {})
          )
        }
        if lookup(volume, "efs", null) != null
      ]
    ]) : pair.key => pair.value
  }

  # Services with load balancer rules
  services_with_lb = {
    for k, v in var.services : k => v if lookup(v, "lb_listener_rule", null) != null
  }

  # Services that are long-running (not scheduled tasks)
  services_running = {
    for k, v in var.services : k => v if !lookup(v, "is_scheduled_task", false)
  }

  # Services that are scheduled tasks (EventBridge cron)
  services_scheduled = {
    for k, v in var.services : k => v if lookup(v, "is_scheduled_task", false)
  }
}

# -------------------------------------------------------
# ECS Cluster
# -------------------------------------------------------

resource "aws_ecs_cluster" "cluster" {
  name = "${var.environment}-${var.ecs_cluster.name}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-cluster"
    }
  )
}

resource "aws_ecs_cluster_capacity_providers" "cluster_cp" {
  cluster_name = aws_ecs_cluster.cluster.name

  capacity_providers = var.ecs_cluster.capacity_providers

  default_capacity_provider_strategy {
    capacity_provider = var.ecs_cluster.default_capacity_provider
    weight            = 1
  }
}

# -------------------------------------------------------
# IAM Roles
# -------------------------------------------------------

resource "aws_iam_role" "execution_role" {
  name = "${var.environment}-${var.ecs_cluster.name}-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "execution_role_policy" {
  name = "${var.environment}-${var.ecs_cluster.name}-execution-policy"
  role = aws_iam_role.execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = distinct([
          for service in var.services :
          data.aws_ecr_repository.repos[service.container.repository].arn
        ])
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          for service in var.services :
          "${aws_cloudwatch_log_group.service_logs[service.container.name].arn}:*"
        ]
      }
    ]
  })
}

resource "aws_iam_role" "task_role" {
  name = "${var.environment}-${var.ecs_cluster.name}-task"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "task_role_policy" {
  name = "${var.environment}-${var.ecs_cluster.name}-task-policy"
  role = aws_iam_role.task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Effect = "Allow"
          Action = [
            "ssmmessages:CreateControlChannel",
            "ssmmessages:CreateDataChannel",
            "ssmmessages:OpenControlChannel",
            "ssmmessages:OpenDataChannel"
          ]
          Resource = "*"
        }
      ],
      # EFS permissions for services that use volumes
      flatten([
        for name, svc in var.services : [
          for volume in coalesce(lookup(svc, "volumes", []), []) : {
            Effect = "Allow"
            Action = [
              "elasticfilesystem:ClientMount",
              "elasticfilesystem:ClientWrite",
              "elasticfilesystem:ClientRootAccess"
            ]
            Resource = [
              aws_efs_file_system.service_volumes["${name}-${volume.name}"].arn
            ]
          }
          if lookup(volume, "efs", null) != null
        ]
      ])
    )
  })

  depends_on = [aws_efs_file_system.service_volumes]
}

# -------------------------------------------------------
# CloudWatch Log Groups
# -------------------------------------------------------

resource "aws_cloudwatch_log_group" "service_logs" {
  for_each = var.services

  name              = "/ecs/${var.environment}-${each.key}"
  retention_in_days = 30

  tags = var.tags
}

# -------------------------------------------------------
# Task Definitions (for all services including scheduled tasks)
# -------------------------------------------------------

resource "aws_ecs_task_definition" "service_task" {
  for_each = var.services

  family                   = "${var.environment}-${each.key}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = each.value.container.cpu
  memory                   = each.value.container.memory
  execution_role_arn       = aws_iam_role.execution_role.arn
  task_role_arn            = aws_iam_role.task_role.arn

  depends_on = [aws_iam_role_policy.execution_role_policy]

  dynamic "volume" {
    for_each = coalesce(lookup(each.value, "volumes", []), [])
    content {
      name = volume.value.name

      efs_volume_configuration {
        file_system_id     = aws_efs_file_system.service_volumes["${each.key}-${volume.value.name}"].id
        root_directory     = "/"
        transit_encryption = "ENABLED"
        authorization_config {
          access_point_id = aws_efs_access_point.service_volumes["${each.key}-${volume.value.name}"].id
          iam             = "ENABLED"
        }
      }
    }
  }

  container_definitions = jsonencode([
    merge(
      {
        name      = each.value.container.name
        image     = "${data.aws_ecr_repository.repos[each.value.container.repository].repository_url}:${each.value.container.tag}"
        cpu       = each.value.container.cpu
        memory    = each.value.container.memory
        essential = true
        portMappings = [{
          containerPort = each.value.container.port
          hostPort      = each.value.container.port
          protocol      = "tcp"
        }]
        environment = each.value.container.environment
        secrets     = lookup(each.value.container, "secrets", [])
        mountPoints = lookup(each.value.container, "mount_points", [])
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            "awslogs-group"         = "/ecs/${var.environment}-${each.key}"
            "awslogs-region"        = var.aws_region
            "awslogs-stream-prefix" = "ecs"
          }
        }
      },
      lookup(each.value.container, "health_check", null) != null ? {
        healthCheck = {
          command     = ["CMD-SHELL", "curl -f http://localhost:${each.value.container.port}${each.value.container.health_check} || exit 1"]
          interval    = 30
          timeout     = 5
          retries     = 3
          startPeriod = 60
        }
      } : {}
    )
  ])

  tags = var.tags
}

# -------------------------------------------------------
# ECS Services (long-running only, not scheduled tasks)
# -------------------------------------------------------

resource "aws_ecs_service" "service" {
  for_each = local.services_running

  name                               = "${var.environment}-${each.key}"
  cluster                            = aws_ecs_cluster.cluster.id
  task_definition                    = aws_ecs_task_definition.service_task[each.key].arn
  desired_count                      = lookup(each.value, "desired_count", 1)
  launch_type                        = "FARGATE"
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = lookup(each.value, "lb_listener_rule", null) != null ? 60 : null
  enable_execute_command             = true

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.service.id]
    assign_public_ip = false
  }

  dynamic "load_balancer" {
    for_each = lookup(each.value, "lb_listener_rule", null) != null ? [1] : []
    content {
      target_group_arn = aws_lb_target_group.service_tg[each.key].arn
      container_name   = each.value.container.name
      container_port   = each.value.container.port
    }
  }

  deployment_controller {
    type = "ECS"
  }

  force_new_deployment = true

  tags = var.tags

  depends_on = [aws_lb_listener_rule.service_rule]
}

# -------------------------------------------------------
# Load Balancer Target Groups & Rules
# -------------------------------------------------------

resource "aws_lb_target_group" "service_tg" {
  for_each = local.services_with_lb

  name        = "${var.environment}-${each.key}-tg"
  port        = each.value.container.port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = lookup(each.value.container, "health_check", "/health")
    healthy_threshold   = 3
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200-299"
    protocol            = "HTTP"
  }

  tags = var.tags
}

resource "aws_lb_listener_rule" "service_rule" {
  for_each = local.services_with_lb

  listener_arn = var.lb_listener_arn

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.service_tg[each.key].arn
  }

  condition {
    path_pattern {
      values = each.value.lb_listener_rule.path_pattern
    }
  }
}

# -------------------------------------------------------
# Auto-scaling
# -------------------------------------------------------

resource "aws_appautoscaling_target" "ecs_target" {
  for_each = {
    for k, v in local.services_running : k => v if lookup(v, "auto_scaling", false)
  }

  max_capacity       = lookup(each.value, "max_capacity", 10)
  min_capacity       = lookup(each.value, "min_capacity", 1)
  resource_id        = "service/${aws_ecs_cluster.cluster.name}/${aws_ecs_service.service[each.key].name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "ecs_policy_cpu" {
  for_each = {
    for k, v in local.services_running : k => v if lookup(v, "auto_scaling", false)
  }

  name               = "${var.environment}-${each.key}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target[each.key].resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target[each.key].scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target[each.key].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    target_value       = lookup(each.value, "scaling_cpu_threshold", 70)
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# -------------------------------------------------------
# Security Groups
# -------------------------------------------------------

resource "aws_security_group" "service" {
  name        = "${var.environment}-${var.ecs_cluster.name}-sg"
  description = "Security group for ECS services"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [var.alb_security_group_id]
    description     = "Allow incoming traffic from ALB"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-${var.ecs_cluster.name}-sg"
    }
  )
}

# EFS security group (only if any service needs volumes)
resource "aws_security_group" "efs" {
  count = length(local.services_with_volumes) > 0 ? 1 : 0

  name        = "${var.environment}-${var.ecs_cluster.name}-efs-sg"
  description = "Security group for EFS volumes"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.service.id]
    description     = "Allow NFS traffic from ECS tasks"
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.environment}-${var.ecs_cluster.name}-efs-sg"
    }
  )
}

# -------------------------------------------------------
# EFS File Systems
# -------------------------------------------------------

resource "aws_efs_file_system" "service_volumes" {
  for_each = local.efs_volume_map

  creation_token   = "${var.environment}-${coalesce(lookup(each.value, "creation_token", null), each.key)}"
  encrypted        = coalesce(lookup(each.value, "encrypted", null), true)
  performance_mode = coalesce(lookup(each.value, "performance_mode", null), "generalPurpose")
  throughput_mode  = coalesce(lookup(each.value, "throughput_mode", null), "bursting")

  tags = merge(var.tags, {
    Name    = "${var.environment}-${each.key}"
    Service = each.value.service_name
  })
}

resource "aws_efs_mount_target" "service_volumes" {
  count = length(local.services_with_volumes) > 0 ? length(var.private_subnet_ids) : 0

  file_system_id  = values(aws_efs_file_system.service_volumes)[0].id
  subnet_id       = var.private_subnet_ids[count.index]
  security_groups = [aws_security_group.efs[0].id]
}

resource "aws_efs_access_point" "service_volumes" {
  for_each = local.efs_volume_map

  file_system_id = aws_efs_file_system.service_volumes[each.key].id

  posix_user {
    gid = tonumber(lookup(each.value, "owner_gid", "1000"))
    uid = tonumber(lookup(each.value, "owner_uid", "1000"))
  }

  root_directory {
    path = lookup(each.value, "root_directory", "/")
    creation_info {
      owner_gid   = tonumber(lookup(each.value, "owner_gid", "1000"))
      owner_uid   = tonumber(lookup(each.value, "owner_uid", "1000"))
      permissions = lookup(each.value, "permissions", "755")
    }
  }

  tags = merge(var.tags, {
    Name    = "${var.environment}-${each.value.service_name}-${each.value.volume_name}-ap"
    Service = each.value.service_name
  })
}

# -------------------------------------------------------
# EventBridge Scheduled Tasks (cron jobs)
# -------------------------------------------------------

# IAM role for EventBridge to run ECS tasks
resource "aws_iam_role" "eventbridge_role" {
  count = length(local.services_scheduled) > 0 ? 1 : 0

  name = "${var.environment}-${var.ecs_cluster.name}-eventbridge"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "events.amazonaws.com"
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "eventbridge_policy" {
  count = length(local.services_scheduled) > 0 ? 1 : 0

  name = "${var.environment}-${var.ecs_cluster.name}-eventbridge-policy"
  role = aws_iam_role.eventbridge_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecs:RunTask"]
        Resource = [for k, v in local.services_scheduled : aws_ecs_task_definition.service_task[k].arn]
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [
          aws_iam_role.execution_role.arn,
          aws_iam_role.task_role.arn
        ]
      }
    ]
  })
}

# EventBridge rules for scheduled tasks
resource "aws_cloudwatch_event_rule" "scheduled_task" {
  for_each = local.services_scheduled

  name                = "${var.environment}-${each.key}"
  description         = "Schedule for ${each.key}"
  schedule_expression = each.value.schedule_expression

  tags = var.tags
}

resource "aws_cloudwatch_event_target" "scheduled_task" {
  for_each = local.services_scheduled

  rule     = aws_cloudwatch_event_rule.scheduled_task[each.key].name
  arn      = aws_ecs_cluster.cluster.arn
  role_arn = aws_iam_role.eventbridge_role[0].arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.service_task[each.key].arn
    launch_type         = "FARGATE"

    network_configuration {
      subnets          = var.private_subnet_ids
      security_groups  = [aws_security_group.service.id]
      assign_public_ip = false
    }
  }
}
