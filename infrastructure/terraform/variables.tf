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

variable "redis_node_type" {
  type    = string
  default = "cache.t4g.micro"
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "worker_desired_count" {
  type    = number
  default = 1
}

variable "beat_desired_count" {
  type    = number
  default = 1
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

variable "extra_environment" {
  type    = map(string)
  default = {}
}
