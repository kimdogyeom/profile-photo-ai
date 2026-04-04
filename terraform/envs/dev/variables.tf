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

variable "hosted_zone_id" {
  type    = string
  default = ""
}

variable "certificate_arn" {
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
