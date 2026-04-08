variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "domain_name" {
  type    = string
  default = ""
}

variable "hosted_zone_name" {
  type    = string
  default = ""

  validation {
    condition     = var.domain_name == "" || var.hosted_zone_name != ""
    error_message = "hosted_zone_name must be set when domain_name is configured."
  }

  validation {
    condition     = var.hosted_zone_name == "" || var.domain_name != ""
    error_message = "domain_name must be set when hosted_zone_name is configured."
  }
}

variable "tags" {
  type    = map(string)
  default = {}
}
