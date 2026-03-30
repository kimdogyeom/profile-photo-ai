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
