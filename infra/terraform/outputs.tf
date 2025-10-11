output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = module.rds.endpoint
  sensitive   = true
}

output "s3_bucket_name" {
  description = "S3 bucket name"
  value       = module.s3.bucket_name
}

output "opensearch_endpoint" {
  description = "OpenSearch endpoint"
  value       = module.opensearch.endpoint
}

output "cognito_user_pool_id" {
  description = "Cognito user pool ID"
  value       = module.cognito.user_pool_id
}

output "cognito_client_id" {
  description = "Cognito client ID"
  value       = module.cognito.client_id
}

output "sqs_queue_url" {
  description = "SQS queue URL"
  value       = module.messaging.queue_url
}

output "sns_topic_arn" {
  description = "SNS topic ARN"
  value       = module.messaging.topic_arn
}

output "acm_pca_arn" {
  description = "ACM Private CA ARN"
  value       = module.acm_pca.ca_arn
}

output "ecr_repositories" {
  description = "ECR repository URLs"
  value       = module.ecr.repository_urls
}

