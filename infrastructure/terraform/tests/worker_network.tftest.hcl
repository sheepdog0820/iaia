# Terraform >= 1.9: all providers are mocked; no AWS resources are created.
mock_provider "aws" {}
mock_provider "random" {}

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
