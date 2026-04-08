variable "project_name" {
  type    = string
  default = "profile-photo-ai"
}

variable "aws_region" {
  type    = string
  default = "ap-northeast-1"
}

variable "state_bucket_name" {
  type    = string
  default = "profile-photo-ai-terraform-state"
}

variable "lock_table_name" {
  type    = string
  default = "profile-photo-ai-terraform-locks"
}

variable "github_repo_owner" {
  type    = string
  default = "kimdogyeom"
}

variable "github_repo_name" {
  type    = string
  default = "profile-photo-ai"
}

variable "github_oidc_url" {
  type    = string
  default = "https://token.actions.githubusercontent.com"
}

variable "github_oidc_client_ids" {
  type    = list(string)
  default = ["sts.amazonaws.com"]
}

variable "github_dev_environment_name" {
  type    = string
  default = "dev"
}

variable "github_prod_environment_name" {
  type    = string
  default = "prod"
}

variable "github_actions_dev_role_name" {
  type    = string
  default = "profile-photo-ai-dev-role"
}

variable "github_actions_prod_role_name" {
  type    = string
  default = "profile-photo-ai-prod-role"
}

variable "github_environment_domain_names" {
  type = map(string)
  default = {
    dev  = ""
    prod = ""
  }
}

variable "github_environment_hosted_zone_names" {
  type = map(string)
  default = {
    dev  = ""
    prod = ""
  }
}
