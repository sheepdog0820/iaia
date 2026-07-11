variable "project_name" {
  type    = string
  default = "tableno"
}

variable "environment" {
  type = string
  validation {
    condition     = contains(["aws-pre", "aws-prod"], var.environment)
    error_message = "environment must be aws-pre or aws-prod."
  }
}

variable "aws_region" {
  type    = string
  default = "ap-northeast-1"
}

variable "offline_plan" {
  description = "Use deterministic AWS metadata and skip credential checks for repository-only plan validation."
  type        = bool
  default     = false
}

variable "domain_name" {
  type = string
}

variable "hosted_zone_id" {
  type = string
}

variable "container_image" {
  type = string
}

variable "db_engine" {
  type    = string
  default = "postgres"
  validation {
    condition     = contains(["postgres", "mysql"], var.db_engine)
    error_message = "db_engine must be postgres or mysql."
  }
}

variable "db_name" {
  type    = string
  default = "tableno"
}

variable "db_username" {
  type    = string
  default = "tableno"
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_allocated_storage" {
  type    = number
  default = 20
}

variable "db_max_allocated_storage" {
  type    = number
  default = 100
}

variable "db_multi_az" {
  type    = bool
  default = false
}

variable "db_backup_retention_period" {
  type    = number
  default = 7
}

variable "db_backup_window" {
  description = "Preferred RDS backup window in UTC."
  type        = string
  default     = null
}

variable "db_performance_insights_enabled" {
  type    = bool
  default = true
}

variable "db_monitoring_interval" {
  type    = number
  default = 0
}

variable "redis_node_type" {
  type    = string
  default = "cache.t4g.micro"
}

variable "enable_nat_gateway" {
  type    = bool
  default = true
}

variable "enable_elasticache" {
  type    = bool
  default = true
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "enable_off_hours_schedule" {
  description = "Stop the pre-environment ECS service and RDS instance outside business hours."
  type        = bool
  default     = false
}

variable "off_hours_schedule_timezone" {
  description = "IANA timezone used by EventBridge Scheduler for off-hours schedules."
  type        = string
  default     = "Asia/Tokyo"
}

variable "enable_worker_service" {
  type    = bool
  default = true
}

variable "worker_desired_count" {
  type    = number
  default = 1
}

variable "enable_beat_service" {
  type    = bool
  default = true
}

variable "beat_desired_count" {
  type    = number
  default = 1
}

variable "web_cpu" {
  type    = number
  default = 512
}

variable "web_memory" {
  type    = number
  default = 1024
}

variable "worker_cpu" {
  type    = number
  default = 512
}

variable "worker_memory" {
  type    = number
  default = 1024
}

variable "beat_cpu" {
  type    = number
  default = 256
}

variable "beat_memory" {
  type    = number
  default = 512
}

variable "site_id" {
  type    = number
  default = 1
}

variable "allowed_hosts_override" {
  description = "Optional explicit ALLOWED_HOSTS value. Leave empty to use domain_name."
  type        = string
  default     = ""
}

variable "secure_ssl_redirect" {
  description = "Whether Django should redirect HTTP to HTTPS. Keep true behind ALB with X-Forwarded-Proto."
  type        = bool
  default     = true
}

variable "enable_deletion_protection" {
  type    = bool
  default = true
}

variable "alarm_email" {
  type      = string
  default   = ""
  sensitive = true
}

variable "monthly_budget_usd" {
  type    = number
  default = 150
}

variable "cloudwatch_log_retention_days" {
  type    = number
  default = 30
}

variable "enable_cloudfront_logging" {
  type    = bool
  default = true
}

variable "enable_s3_access_logging" {
  type    = bool
  default = true
}

variable "extra_environment" {
  type    = map(string)
  default = {}
}

variable "extra_secret_names" {
  description = "Additional JSON keys in the app Secrets Manager secret to inject as ECS container secrets. Values are managed outside Terraform."
  type        = list(string)
  default     = []
}
