# Terraform >= 1.9: all providers are mocked; no AWS resources are created.
mock_provider "aws" {}
mock_provider "random" {}

override_resource {
  target          = aws_elasticache_replication_group.main
  override_during = plan
  values          = { primary_endpoint_address = "redis.example.invalid" }
}

override_resource {
  target          = aws_acm_certificate_validation.app
  override_during = plan
  values = {
    certificate_arn = "arn:aws:acm:ap-northeast-1:000000000000:certificate/00000000-0000-0000-0000-000000000000"
  }
}

override_resource {
  override_during = plan
  target          = aws_acm_certificate.app
  values = {
    arn = "arn:aws:acm:ap-northeast-1:000000000000:certificate/00000000-0000-0000-0000-000000000000"
    domain_validation_options = [{
      domain_name           = "pre.example.invalid"
      resource_record_name  = "_validation.pre.example.invalid"
      resource_record_value = "_validation.acm-validations.aws"
      resource_record_type  = "CNAME"
    }]
  }
}

override_resource {
  override_during = plan
  target          = aws_subnet.public
  values          = { id = "subnet-public" }
}

override_resource {
  override_during = plan
  target          = aws_subnet.private
  values          = { id = "subnet-private" }
}

variables {
  offline_plan          = true
  environment           = "aws-pre"
  domain_name           = "pre.example.invalid"
  hosted_zone_id        = "Z0000000000000"
  container_image       = "000000000000.dkr.ecr.ap-northeast-1.amazonaws.com/tableno:validation"
  enable_worker_service = true
  enable_beat_service   = true
}

run "without_nat" {
  command = plan
  variables {
    enable_nat_gateway = false
  }
  assert {
    condition     = aws_ecs_service.worker[0].network_configuration[0].assign_public_ip && aws_ecs_service.beat[0].network_configuration[0].assign_public_ip
    error_message = "Without NAT, both background services need a public IP for outbound access."
  }
  assert {
    condition     = aws_ecs_service.worker[0].network_configuration[0].subnets == toset(["subnet-public"]) && aws_ecs_service.beat[0].network_configuration[0].subnets == toset(["subnet-public"])
    error_message = "Without NAT, background services must use the public subnet route."
  }
}

run "with_nat" {
  command = plan
  variables {
    enable_nat_gateway = true
  }
  assert {
    condition     = !aws_ecs_service.worker[0].network_configuration[0].assign_public_ip && !aws_ecs_service.beat[0].network_configuration[0].assign_public_ip
    error_message = "With NAT, background services must keep private addresses."
  }
  assert {
    condition     = aws_ecs_service.worker[0].network_configuration[0].subnets == toset(["subnet-private"]) && aws_ecs_service.beat[0].network_configuration[0].subnets == toset(["subnet-private"])
    error_message = "With NAT, background services must use private subnets."
  }
}

run "broker_only_keeps_database_sessions" {
  command = plan
  variables {
    enable_elasticache     = true
    enable_redis_web_state = false
  }
  assert {
    condition = alltrue([
      for item in local.app_base_environment : item.value == "false"
      if contains(["USE_REDIS_CACHE", "WEBSOCKET_NOTIFICATIONS_ENABLED"], item.name)
    ]) && one([for item in local.app_base_environment : item.value if item.name == "SESSION_ENGINE"]) == "django.contrib.sessions.backends.db"
    error_message = "Broker-only Redis must preserve database sessions and existing web state settings."
  }
  assert {
    condition = alltrue([
      for item in local.app_redis_environment : item.value == "rediss://redis.example.invalid:6379/0?ssl_cert_reqs=required"
      if contains(["CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"], item.name)
    ]) && length([for item in local.app_redis_environment : item if contains(["CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"], item.name)]) == 2
    error_message = "Broker-only mode must still supply both Celery URLs with certificate verification."
  }
}

run "default_redis_preserves_existing_behavior" {
  command = plan
  assert {
    condition = alltrue([
      for item in local.app_base_environment : item.value == "true"
      if contains(["USE_REDIS_CACHE", "WEBSOCKET_NOTIFICATIONS_ENABLED"], item.name)
    ]) && one([for item in local.app_base_environment : item.value if item.name == "SESSION_ENGINE"]) == "django.contrib.sessions.backends.cache"
    error_message = "Existing Redis deployments must retain their web state defaults."
  }
}

run "without_redis" {
  command = plan
  variables {
    enable_elasticache = false
  }
  assert {
    condition = length(local.app_redis_environment) == 0 && alltrue([
      for item in local.app_base_environment : item.value == "false"
      if contains(["USE_REDIS_CACHE", "WEBSOCKET_NOTIFICATIONS_ENABLED"], item.name)
    ]) && one([for item in local.app_base_environment : item.value if item.name == "SESSION_ENGINE"]) == "django.contrib.sessions.backends.db"
    error_message = "Disabled Redis must not leave enabled web state settings or Celery URLs."
  }
}
