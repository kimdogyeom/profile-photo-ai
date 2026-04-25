variable "project_name" {
  type    = string
  default = "profile-photo-ai"
}

variable "environment" {
  type = string
}

variable "aws_region" {
  type    = string
  default = "ap-northeast-1"
}

variable "bedrock_region" {
  type    = string
  default = "ap-northeast-1"
}

variable "bedrock_model_id" {
  type    = string
  default = "amazon.nova-canvas-v1:0"
}

variable "daily_limit" {
  type    = number
  default = 15
}

variable "domain_name" {
  type    = string
  default = ""
}

variable "hosted_zone_name" {
  type    = string
  default = ""
}

variable "acm_certificate_arn" {
  type    = string
  default = ""
}

variable "discord_webhook_url" {
  type      = string
  default   = ""
  sensitive = true
}

variable "cors_allowed_origins" {
  type    = list(string)
  default = ["*"]
}

variable "lambda_artifact_paths" {
  type = map(string)
}

variable "tags" {
  type    = map(string)
  default = {}
}
