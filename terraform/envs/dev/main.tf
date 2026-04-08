terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.95"
    }
  }

  backend "s3" {}
}

provider "aws" {
  region = var.aws_region
}

provider "aws" {
  alias  = "use1"
  region = "us-east-1"
}

locals {
  lambda_artifact_paths = {
    file_transfer    = abspath("${path.root}/../../../dist/lambda/file-transfer.zip")
    api_manager      = abspath("${path.root}/../../../dist/lambda/api-manager.zip")
    image_process    = abspath("${path.root}/../../../dist/lambda/image-process.zip")
    stats_aggregator = abspath("${path.root}/../../../dist/lambda/stats-aggregator.zip")
    webhook_notifier = abspath("${path.root}/../../../dist/lambda/webhook-notifier.zip")
  }
}

module "app" {
  source = "../../modules/app_stack"
  providers = {
    aws      = aws
    aws.use1 = aws.use1
  }
  environment           = "dev"
  aws_region            = var.aws_region
  bedrock_region        = var.bedrock_region
  bedrock_model_id      = var.bedrock_model_id
  daily_limit           = var.daily_limit
  domain_name           = var.domain_name
  hosted_zone_name      = var.hosted_zone_name
  discord_webhook_url   = var.discord_webhook_url
  cors_allowed_origins  = var.cors_allowed_origins
  lambda_artifact_paths = local.lambda_artifact_paths
}

output "api_base_url" {
  value = module.app.api_base_url
}

output "frontend_bucket_name" {
  value = module.app.frontend_bucket_name
}

output "frontend_distribution_id" {
  value = module.app.frontend_distribution_id
}

output "frontend_url" {
  value = module.app.frontend_url
}

output "cognito_user_pool_id" {
  value = module.app.cognito_user_pool_id
}

output "cognito_user_pool_client_id" {
  value = module.app.cognito_user_pool_client_id
}

output "aws_region" {
  value = var.aws_region
}
