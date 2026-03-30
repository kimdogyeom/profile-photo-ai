variable "function_name" {
  type = string
}

variable "description" {
  type    = string
  default = null
}

variable "handler" {
  type = string
}

variable "runtime" {
  type    = string
  default = "python3.12"
}

variable "timeout" {
  type    = number
  default = 30
}

variable "memory_size" {
  type    = number
  default = 512
}

variable "source_zip" {
  type = string
}

variable "environment_variables" {
  type    = map(string)
  default = {}
}

variable "managed_policy_arns" {
  type = list(string)
  default = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess",
  ]
}

variable "policy_json" {
  type    = string
  default = null
}

variable "log_retention_in_days" {
  type    = number
  default = 14
}

variable "tracing_mode" {
  type    = string
  default = "Active"
}

variable "architectures" {
  type    = list(string)
  default = ["x86_64"]
}

variable "tags" {
  type    = map(string)
  default = {}
}
