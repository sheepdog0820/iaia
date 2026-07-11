data "aws_availability_zones" "available" {
  count = var.offline_plan ? 0 : 1
  state = "available"
}

data "aws_caller_identity" "current" {
  count = var.offline_plan ? 0 : 1
}

locals {
  name = "${var.project_name}-${var.environment}"
  availability_zones = var.offline_plan ? [
    "${var.aws_region}a",
    "${var.aws_region}c",
  ] : data.aws_availability_zones.available[0].names
  account_id = var.offline_plan ? "000000000000" : data.aws_caller_identity.current[0].account_id
  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
  db_port          = var.db_engine == "postgres" ? 5432 : 3306
  redis_url        = var.enable_elasticache ? "rediss://${aws_elasticache_replication_group.main[0].primary_endpoint_address}:6379/0" : ""
  celery_redis_url = var.enable_elasticache ? "${local.redis_url}?ssl_cert_reqs=CERT_NONE" : ""
  allowed_hosts    = var.allowed_hosts_override != "" ? var.allowed_hosts_override : var.domain_name
  backup_retention = var.environment == "aws-prod" ? 14 : var.db_backup_retention_period
  app_secret_names = distinct(concat(["SECRET_KEY", "DB_PASSWORD"], var.extra_secret_names))
  app_container_secrets = [
    for secret_name in local.app_secret_names : {
      name      = secret_name
      valueFrom = "${aws_secretsmanager_secret.app.arn}:${secret_name}::"
    }
  ]
  app_base_environment = [
    { name = "APP_ENV", value = var.environment },
    { name = "DB_ENGINE", value = var.db_engine },
    { name = "DB_HOST", value = aws_db_instance.main.address },
    { name = "DB_PORT", value = tostring(local.db_port) },
    { name = "DB_NAME", value = var.db_name },
    { name = "DB_USER", value = var.db_username },
    { name = "DB_SSL_MODE", value = "require" },
    { name = "USE_REDIS_CACHE", value = tostring(var.enable_elasticache) },
    { name = "WEBSOCKET_NOTIFICATIONS_ENABLED", value = tostring(var.enable_elasticache) },
    { name = "SESSION_ENGINE", value = var.enable_elasticache ? "django.contrib.sessions.backends.cache" : "django.contrib.sessions.backends.db" },
    { name = "USE_S3_STORAGE", value = "True" },
    { name = "AWS_STORAGE_BUCKET_NAME", value = aws_s3_bucket.assets.id },
    { name = "AWS_S3_REGION_NAME", value = var.aws_region },
    { name = "AWS_S3_CUSTOM_DOMAIN", value = aws_cloudfront_distribution.assets.domain_name },
    { name = "ALLOWED_HOSTS", value = local.allowed_hosts },
    { name = "CSRF_TRUSTED_ORIGINS", value = "https://${var.domain_name}" },
    { name = "SECURE_SSL_REDIRECT", value = tostring(var.secure_ssl_redirect) },
    { name = "SITE_ID", value = tostring(var.site_id) },
    { name = "LOG_TO_STDOUT", value = "True" }
  ]
  app_redis_environment = var.enable_elasticache ? [
    { name = "REDIS_URL", value = local.redis_url },
    { name = "REDIS_SSL_CERT_REQS", value = "none" },
    { name = "CELERY_BROKER_URL", value = local.celery_redis_url },
    { name = "CELERY_RESULT_BACKEND", value = local.celery_redis_url },
  ] : []
  app_container_environment = concat(
    local.app_base_environment,
    local.app_redis_environment,
    [for key, value in var.extra_environment : { name = key, value = value }],
  )
  maintenance_response_html = <<-HTML
    <!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>メンテナンス中 | タブレノ</title><style>body{margin:0;background:#f4f1ea;color:#28323c;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;display:grid;min-height:100vh;place-items:center}.card{box-sizing:border-box;width:min(92%,560px);padding:40px 28px;border-radius:20px;background:#fff;box-shadow:0 14px 40px #24303b1f;text-align:center}.mark{display:inline-grid;width:64px;height:64px;border-radius:50%;background:#e7f0ee;color:#28665d;place-items:center;font-size:30px;font-weight:700}h1{margin:20px 0 12px;font-size:26px}p{margin:8px 0;line-height:1.7}.time{margin-top:20px;padding:12px;border-radius:12px;background:#f4f7f6;font-weight:700}</style></head><body><main class="card"><div class="mark">i</div><h1>ただいまメンテナンス中です</h1><p>タブレノをご利用いただきありがとうございます。</p><p>毎日 02:00〜08:05 は開発環境のメンテナンス時間です。</p><div class="time">08:05頃に再開予定です</div></main></body></html>
  HTML
}

resource "aws_vpc" "main" {
  cidr_block           = "10.40.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${local.name}-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.name}-igw" }
}

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  availability_zone       = local.availability_zones[count.index]
  map_public_ip_on_launch = true
  tags                    = { Name = "${local.name}-public-${count.index + 1}" }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index + 10)
  availability_zone = local.availability_zones[count.index]
  tags              = { Name = "${local.name}-private-${count.index + 1}" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = { Name = "${local.name}-public" }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_eip" "nat" {
  count  = var.enable_nat_gateway ? 1 : 0
  domain = "vpc"
  tags   = { Name = "${local.name}-nat" }
}

resource "aws_nat_gateway" "main" {
  count         = var.enable_nat_gateway ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = aws_subnet.public[0].id
  depends_on    = [aws_internet_gateway.main]
  tags          = { Name = "${local.name}-nat" }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  dynamic "route" {
    for_each = var.enable_nat_gateway ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = aws_nat_gateway.main[0].id
    }
  }
  tags = { Name = "${local.name}-private" }
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

resource "aws_security_group" "alb" {
  name   = "${local.name}-alb"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "ecs" {
  name   = "${local.name}-ecs"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "data" {
  name   = "${local.name}-data"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port       = local.db_port
    to_port         = local.db_port
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }
  dynamic "ingress" {
    for_each = var.enable_elasticache ? [1] : []
    content {
      from_port       = 6379
      to_port         = 6379
      protocol        = "tcp"
      security_groups = [aws_security_group.ecs.id]
    }
  }
}

resource "random_password" "secret_key" {
  length  = 64
  special = false
}

resource "random_password" "db_password" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "app" {
  name                    = "${local.name}/app"
  recovery_window_in_days = var.environment == "aws-prod" ? 30 : 0
}

resource "aws_secretsmanager_secret_version" "app" {
  secret_id = aws_secretsmanager_secret.app.id
  secret_string = jsonencode({
    SECRET_KEY  = random_password.secret_key.result
    DB_PASSWORD = random_password.db_password.result
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_db_subnet_group" "main" {
  name       = local.name
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "main" {
  identifier                   = local.name
  engine                       = var.db_engine
  instance_class               = var.db_instance_class
  allocated_storage            = var.db_allocated_storage
  max_allocated_storage        = var.db_max_allocated_storage
  storage_encrypted            = true
  db_name                      = var.db_name
  username                     = var.db_username
  password                     = random_password.db_password.result
  port                         = local.db_port
  db_subnet_group_name         = aws_db_subnet_group.main.name
  vpc_security_group_ids       = [aws_security_group.data.id]
  backup_retention_period      = local.backup_retention
  backup_window                = var.db_backup_window
  deletion_protection          = var.enable_deletion_protection
  skip_final_snapshot          = !var.enable_deletion_protection
  multi_az                     = var.db_multi_az
  performance_insights_enabled = var.environment == "aws-prod" ? true : var.db_performance_insights_enabled
  monitoring_interval          = var.db_monitoring_interval
  apply_immediately            = var.environment != "aws-prod"
}

resource "aws_elasticache_subnet_group" "main" {
  count      = var.enable_elasticache ? 1 : 0
  name       = local.name
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_replication_group" "main" {
  count                      = var.enable_elasticache ? 1 : 0
  replication_group_id       = local.name
  description                = "Tableno Redis"
  node_type                  = var.redis_node_type
  port                       = 6379
  parameter_group_name       = "default.redis7"
  subnet_group_name          = aws_elasticache_subnet_group.main[0].name
  security_group_ids         = [aws_security_group.data.id]
  transit_encryption_enabled = true
  at_rest_encryption_enabled = true
  automatic_failover_enabled = var.environment == "aws-prod"
  multi_az_enabled           = var.environment == "aws-prod"
  num_cache_clusters         = var.environment == "aws-prod" ? 2 : 1
}

resource "aws_s3_bucket" "assets" {
  bucket        = "${local.name}-assets-${local.account_id}"
  force_destroy = var.environment != "aws-prod"
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket                  = aws_s3_bucket.assets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_cloudfront_origin_access_control" "assets" {
  name                              = local.name
  description                       = "OAC for Tableno assets"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "assets" {
  enabled = true
  origin {
    domain_name              = aws_s3_bucket.assets.bucket_regional_domain_name
    origin_id                = "assets"
    origin_access_control_id = aws_cloudfront_origin_access_control.assets.id
  }
  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "assets"
    viewer_protocol_policy = "redirect-to-https"
    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }
  }
  restrictions {
    geo_restriction { restriction_type = "none" }
  }
  viewer_certificate { cloudfront_default_certificate = true }
}

resource "aws_s3_bucket_policy" "assets" {
  bucket = aws_s3_bucket.assets.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.assets.arn}/*"
      Condition = { StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.assets.arn } }
    }]
  })
}

resource "aws_acm_certificate" "app" {
  domain_name       = var.domain_name
  validation_method = "DNS"
}

resource "aws_route53_record" "certificate" {
  for_each = {
    for option in aws_acm_certificate.app.domain_validation_options :
    option.domain_name => {
      name   = option.resource_record_name
      record = option.resource_record_value
      type   = option.resource_record_type
    }
  }
  zone_id = var.hosted_zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "app" {
  certificate_arn         = aws_acm_certificate.app.arn
  validation_record_fqdns = [for record in aws_route53_record.certificate : record.fqdn]
}

resource "aws_lb" "app" {
  name               = substr(local.name, 0, 32)
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
}

resource "aws_lb_target_group" "app" {
  name        = substr(local.name, 0, 32)
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.main.id
  health_check {
    path                = "/health/live"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.app.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = aws_acm_certificate_validation.app.certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

resource "aws_route53_record" "app" {
  zone_id = var.hosted_zone_id
  name    = var.domain_name
  type    = "A"
  alias {
    name                   = aws_lb.app.dns_name
    zone_id                = aws_lb.app.zone_id
    evaluate_target_health = true
  }
}

resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${local.name}"
  retention_in_days = var.environment == "aws-prod" ? 90 : var.cloudwatch_log_retention_days
}

resource "aws_iam_role" "ecs_execution" {
  name = "${local.name}-ecs-execution"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_secrets" {
  role = aws_iam_role.ecs_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = aws_secretsmanager_secret.app.arn
    }]
  })
}

resource "aws_iam_role" "ecs_task" {
  name = "${local.name}-ecs-task"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ecs-tasks.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "ecs_assets" {
  role = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
      Resource = [aws_s3_bucket.assets.arn, "${aws_s3_bucket.assets.arn}/*"]
    }]
  })
}

resource "aws_ecs_cluster" "app" {
  name = local.name
}

resource "aws_ecs_task_definition" "app" {
  family                   = local.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.web_cpu
  memory                   = var.web_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn
  container_definitions = jsonencode([{
    name         = "web"
    image        = var.container_image
    essential    = true
    portMappings = [{ containerPort = 8000, hostPort = 8000, protocol = "tcp" }]
    environment  = local.app_container_environment
    secrets      = local.app_container_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.app.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "web"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')\""]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${local.name}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn
  container_definitions = jsonencode([{
    name        = "worker"
    image       = var.container_image
    essential   = true
    command     = ["celery", "-A", "tableno", "worker", "--loglevel=info"]
    environment = local.app_container_environment
    secrets     = local.app_container_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.app.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "worker"
      }
    }
  }])
}

resource "aws_ecs_task_definition" "beat" {
  family                   = "${local.name}-beat"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.beat_cpu
  memory                   = var.beat_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn
  container_definitions = jsonencode([{
    name        = "beat"
    image       = var.container_image
    essential   = true
    command     = ["celery", "-A", "tableno", "beat", "--loglevel=info"]
    environment = local.app_container_environment
    secrets     = local.app_container_secrets
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.app.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "beat"
      }
    }
  }])
}

resource "aws_ecs_service" "app" {
  name                               = local.name
  cluster                            = aws_ecs_cluster.app.id
  task_definition                    = aws_ecs_task_definition.app.arn
  desired_count                      = var.desired_count
  launch_type                        = "FARGATE"
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  network_configuration {
    subnets          = var.enable_nat_gateway ? aws_subnet.private[*].id : aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = !var.enable_nat_gateway
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "web"
    container_port   = 8000
  }
  depends_on = [aws_lb_listener.https]
}

resource "aws_iam_role" "off_hours_scheduler" {
  count = var.enable_off_hours_schedule ? 1 : 0
  name  = "${local.name}-off-hours-scheduler"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "off_hours_scheduler" {
  count = var.enable_off_hours_schedule ? 1 : 0
  name  = "${local.name}-off-hours-scheduler"
  role  = aws_iam_role.off_hours_scheduler[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecs:UpdateService"]
        Resource = "arn:aws:ecs:${var.aws_region}:${local.account_id}:service/${local.name}/${local.name}"
      },
      {
        Effect = "Allow"
        Action = [
          "rds:StartDBInstance",
          "rds:StopDBInstance",
        ]
        Resource = "arn:aws:rds:${var.aws_region}:${local.account_id}:db:${local.name}"
      },
      {
        Effect   = "Allow"
        Action   = ["elasticloadbalancing:ModifyListener"]
        Resource = aws_lb_listener.https.arn
      },
    ]
  })
}

locals {
  off_hours_schedules = var.enable_off_hours_schedule ? {
    maintenance_on = {
      description = "Show the Tableno maintenance page before ECS stops at 01:59 JST"
      schedule    = "cron(59 1 * * ? *)"
      target_arn  = "arn:aws:scheduler:::aws-sdk:elasticloadbalancingv2:modifyListener"
      input = jsonencode({
        ListenerArn = aws_lb_listener.https.arn
        DefaultActions = [{
          Type = "fixed-response"
          FixedResponseConfig = {
            StatusCode  = "503"
            ContentType = "text/html"
            MessageBody = trimspace(local.maintenance_response_html)
          }
        }]
      })
    }
    ecs_stop = {
      description = "Scale the Tableno pre ECS service to zero at 02:00 JST"
      schedule    = "cron(0 2 * * ? *)"
      target_arn  = "arn:aws:scheduler:::aws-sdk:ecs:updateService"
      input = jsonencode({
        Cluster      = local.name
        Service      = local.name
        DesiredCount = 0
      })
    }
    rds_stop = {
      description = "Stop the Tableno pre RDS instance after ECS at 02:05 JST"
      schedule    = "cron(5 2 * * ? *)"
      target_arn  = "arn:aws:scheduler:::aws-sdk:rds:stopDBInstance"
      input       = jsonencode({ DbInstanceIdentifier = local.name })
    }
    rds_start = {
      description = "Start the Tableno pre RDS instance before ECS at 07:30 JST"
      schedule    = "cron(30 7 * * ? *)"
      target_arn  = "arn:aws:scheduler:::aws-sdk:rds:startDBInstance"
      input       = jsonencode({ DbInstanceIdentifier = local.name })
    }
    ecs_start = {
      description = "Scale the Tableno pre ECS service to its configured count at 08:00 JST"
      schedule    = "cron(0 8 * * ? *)"
      target_arn  = "arn:aws:scheduler:::aws-sdk:ecs:updateService"
      input = jsonencode({
        Cluster      = local.name
        Service      = local.name
        DesiredCount = var.desired_count
      })
    }
    maintenance_off = {
      description = "Restore normal ALB forwarding after ECS starts at 08:05 JST"
      schedule    = "cron(5 8 * * ? *)"
      target_arn  = "arn:aws:scheduler:::aws-sdk:elasticloadbalancingv2:modifyListener"
      input = jsonencode({
        ListenerArn = aws_lb_listener.https.arn
        DefaultActions = [{
          Type           = "forward"
          TargetGroupArn = aws_lb_target_group.app.arn
        }]
      })
    }
  } : {}
}

resource "aws_scheduler_schedule" "off_hours" {
  for_each = local.off_hours_schedules

  name                         = "${local.name}-${replace(each.key, "_", "-")}"
  description                  = each.value.description
  schedule_expression          = each.value.schedule
  schedule_expression_timezone = var.off_hours_schedule_timezone
  state                        = "ENABLED"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = each.value.target_arn
    role_arn = aws_iam_role.off_hours_scheduler[0].arn
    input    = each.value.input

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 3
    }
  }
}

resource "aws_ecs_service" "worker" {
  count                              = var.enable_worker_service ? 1 : 0
  name                               = "${local.name}-worker"
  cluster                            = aws_ecs_cluster.app.id
  task_definition                    = aws_ecs_task_definition.worker.arn
  desired_count                      = var.worker_desired_count
  launch_type                        = "FARGATE"
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }
}

resource "aws_ecs_service" "beat" {
  count                              = var.enable_beat_service ? 1 : 0
  name                               = "${local.name}-beat"
  cluster                            = aws_ecs_cluster.app.id
  task_definition                    = aws_ecs_task_definition.beat.arn
  desired_count                      = var.beat_desired_count
  launch_type                        = "FARGATE"
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }
}

resource "aws_sns_topic" "alarms" {
  name = "${local.name}-alarms"
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.alarm_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  alarm_name          = "${local.name}-alb-5xx"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  dimensions          = { LoadBalancer = aws_lb.app.arn_suffix }
  alarm_actions       = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "ecs_cpu" {
  alarm_name          = "${local.name}-ecs-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  dimensions          = { ClusterName = aws_ecs_cluster.app.name, ServiceName = aws_ecs_service.app.name }
  alarm_actions       = [aws_sns_topic.alarms.arn]
}

resource "aws_cloudwatch_metric_alarm" "ecs_memory" {
  alarm_name          = "${local.name}-ecs-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  dimensions          = { ClusterName = aws_ecs_cluster.app.name, ServiceName = aws_ecs_service.app.name }
  alarm_actions       = [aws_sns_topic.alarms.arn]
}

resource "aws_budgets_budget" "monthly" {
  name         = "${local.name}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
}
