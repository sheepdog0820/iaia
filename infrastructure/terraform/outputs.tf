output "application_url" {
  value = "https://${var.domain_name}"
}

output "assets_bucket" {
  value = aws_s3_bucket.assets.id
}

output "cloudfront_domain" {
  value = aws_cloudfront_distribution.assets.domain_name
}

output "rds_endpoint" {
  value = aws_db_instance.main.address
}

output "redis_endpoint" {
  value = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "alarm_topic_arn" {
  value = aws_sns_topic.alarms.arn
}
