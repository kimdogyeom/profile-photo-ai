terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      configuration_aliases = [aws.use1]
    }
  }
}

locals {
  common_tags = merge(var.tags, {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  })

  upload_bucket_name      = "${var.project_name}-uploads-raw-${var.environment}"
  result_bucket_name      = "${var.project_name}-results-final-${var.environment}"
  log_archive_bucket_name = "${var.project_name}-logs-archive-${var.environment}"

  users_table_name      = "${var.project_name}-users-${var.environment}"
  usage_log_table_name  = "${var.project_name}-usage-log-${var.environment}"
  image_jobs_table_name = "${var.project_name}-image-jobs-${var.environment}"

  image_process_queue_name = "${var.project_name}-image-process-${var.environment}"
  image_process_dlq_name   = "${var.project_name}-image-process-dlq-${var.environment}"

  file_transfer_function_name    = "${var.project_name}-file-transfer-${var.environment}"
  api_manager_function_name      = "${var.project_name}-api-manager-${var.environment}"
  image_process_function_name    = "${var.project_name}-image-process-${var.environment}"
  stats_aggregator_function_name = "${var.project_name}-stats-aggregator-${var.environment}"
  webhook_notifier_function_name = "${var.project_name}-webhook-notifier-${var.environment}"

  alarm_topic_name = "${var.project_name}-alarm-notifications-${var.environment}"
  metric_namespace = "ProfilePhotoAI/${var.environment}"
}

resource "aws_s3_bucket" "upload" {
  bucket        = local.upload_bucket_name
  force_destroy = true
  tags          = local.common_tags
}

resource "aws_s3_bucket_versioning" "upload" {
  bucket = aws_s3_bucket.upload.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "upload" {
  bucket                  = aws_s3_bucket.upload.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "upload" {
  bucket = aws_s3_bucket.upload.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_cors_configuration" "upload" {
  bucket = aws_s3_bucket.upload.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["POST"]
    allowed_origins = var.cors_allowed_origins
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "upload" {
  bucket = aws_s3_bucket.upload.id

  rule {
    id     = "DeleteOldUploads"
    status = "Enabled"

    filter {}

    expiration {
      days = 7
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }
  }
}

resource "aws_s3_bucket" "result" {
  bucket        = local.result_bucket_name
  force_destroy = true
  tags          = local.common_tags
}

resource "aws_s3_bucket_versioning" "result" {
  bucket = aws_s3_bucket.result.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "result" {
  bucket                  = aws_s3_bucket.result.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "result" {
  bucket = aws_s3_bucket.result.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_cors_configuration" "result" {
  bucket = aws_s3_bucket.result.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET"]
    allowed_origins = var.cors_allowed_origins
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "result" {
  bucket = aws_s3_bucket.result.id

  rule {
    id     = "DeleteOldResults"
    status = "Enabled"

    filter {}

    expiration {
      days = 30
    }

    noncurrent_version_expiration {
      noncurrent_days = 1
    }
  }
}

resource "aws_s3_bucket" "log_archive" {
  bucket        = local.log_archive_bucket_name
  force_destroy = true
  tags          = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "log_archive" {
  bucket                  = aws_s3_bucket.log_archive.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "log_archive" {
  bucket = aws_s3_bucket.log_archive.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "log_archive" {
  bucket = aws_s3_bucket.log_archive.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "log_archive" {
  bucket = aws_s3_bucket.log_archive.id

  rule {
    id     = "TransitionToGlacier"
    status = "Enabled"

    filter {}

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

resource "aws_dynamodb_table" "users" {
  name         = local.users_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userId"

  attribute {
    name = "userId"
    type = "S"
  }

  tags = local.common_tags
}

resource "aws_dynamodb_table" "usage_log" {
  name         = local.usage_log_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "userIdDate"

  attribute {
    name = "userIdDate"
    type = "S"
  }

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "date"
    type = "S"
  }

  global_secondary_index {
    name            = "UserIdIndex"
    hash_key        = "userId"
    range_key       = "date"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = local.common_tags
}

resource "aws_dynamodb_table" "image_jobs" {
  name         = local.image_jobs_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "jobId"

  attribute {
    name = "jobId"
    type = "S"
  }

  attribute {
    name = "userId"
    type = "S"
  }

  attribute {
    name = "createdAt"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "updatedAt"
    type = "S"
  }

  global_secondary_index {
    name            = "UserIdCreatedAtIndex"
    hash_key        = "userId"
    range_key       = "createdAt"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "StatusIndex"
    hash_key        = "status"
    range_key       = "updatedAt"
    projection_type = "ALL"
  }

  tags = local.common_tags
}

resource "aws_sqs_queue" "image_process_dlq" {
  name                      = local.image_process_dlq_name
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
  tags                      = local.common_tags
}

resource "aws_sqs_queue" "image_process" {
  name                       = local.image_process_queue_name
  visibility_timeout_seconds = 900
  message_retention_seconds  = 345600
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.image_process_dlq.arn
    maxReceiveCount     = 3
  })

  tags = local.common_tags
}

resource "aws_sns_topic" "alarm_notifications" {
  name = local.alarm_topic_name
  tags = local.common_tags
}

module "frontend_site" {
  source = "../frontend_site"
  providers = {
    aws      = aws
    aws.use1 = aws.use1
  }
  project_name     = var.project_name
  environment      = var.environment
  domain_name      = var.domain_name
  hosted_zone_name = var.hosted_zone_name
  tags             = local.common_tags
}

resource "aws_cognito_user_pool" "this" {
  name = "${var.project_name}-users-${var.environment}"

  auto_verified_attributes = ["email"]
  username_attributes      = ["email"]
  mfa_configuration        = "OFF"

  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
  }

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  admin_create_user_config {
    allow_admin_create_user_only = false
  }

  schema {
    attribute_data_type = "String"
    mutable             = true
    name                = "email"
    required            = true
  }

  schema {
    attribute_data_type = "String"
    mutable             = true
    name                = "name"
    required            = false
  }

  tags = local.common_tags
}

resource "aws_cognito_user_pool_client" "this" {
  name                          = "${var.project_name}-client-${var.environment}"
  user_pool_id                  = aws_cognito_user_pool.this.id
  generate_secret               = false
  prevent_user_existence_errors = "ENABLED"
  explicit_auth_flows           = ["ALLOW_USER_PASSWORD_AUTH", "ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
  supported_identity_providers  = ["COGNITO"]
  refresh_token_validity        = 30
  access_token_validity         = 1
  id_token_validity             = 1

  token_validity_units {
    refresh_token = "days"
    access_token  = "hours"
    id_token      = "hours"
  }
}

data "aws_iam_policy_document" "file_transfer" {
  statement {
    sid     = "UploadBucketWrite"
    effect  = "Allow"
    actions = ["s3:PutObject"]
    resources = [
      "${aws_s3_bucket.upload.arn}/*",
    ]
  }
}

module "file_transfer" {
  source               = "../lambda_function"
  function_name        = local.file_transfer_function_name
  description          = "Generate authenticated S3 upload forms"
  handler              = "file_transfer.lambda_handler"
  source_zip           = var.lambda_artifact_paths["file_transfer"]
  create_inline_policy = true
  policy_json          = data.aws_iam_policy_document.file_transfer.json
  environment_variables = {
    UPLOAD_BUCKET                = aws_s3_bucket.upload.bucket
    PRESIGNED_URL_EXPIRATION     = "3600"
    POWERTOOLS_SERVICE_NAME      = "ProfilePhotoAI"
    POWERTOOLS_METRICS_NAMESPACE = "ProfilePhotoAI/Metrics"
  }
  tags = local.common_tags
}

data "aws_iam_policy_document" "api_manager" {
  statement {
    sid    = "UsersTableAccess"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:Query",
    ]
    resources = [
      aws_dynamodb_table.users.arn,
      aws_dynamodb_table.usage_log.arn,
      aws_dynamodb_table.image_jobs.arn,
      "${aws_dynamodb_table.usage_log.arn}/index/*",
      "${aws_dynamodb_table.image_jobs.arn}/index/*",
    ]
  }

  statement {
    sid    = "UploadBucketRead"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:HeadObject",
    ]
    resources = ["${aws_s3_bucket.upload.arn}/*"]
  }

  statement {
    sid    = "ResultBucketRead"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:HeadObject",
    ]
    resources = ["${aws_s3_bucket.result.arn}/*"]
  }

  statement {
    sid    = "QueueSend"
    effect = "Allow"
    actions = [
      "sqs:SendMessage",
      "sqs:GetQueueAttributes",
    ]
    resources = [aws_sqs_queue.image_process.arn]
  }
}

module "api_manager" {
  source               = "../lambda_function"
  function_name        = local.api_manager_function_name
  description          = "Manage authenticated image generation jobs"
  handler              = "api_manager.lambda_handler"
  timeout              = 60
  source_zip           = var.lambda_artifact_paths["api_manager"]
  create_inline_policy = true
  policy_json          = data.aws_iam_policy_document.api_manager.json
  environment_variables = {
    SQS_QUEUE_URL                = aws_sqs_queue.image_process.id
    UPLOAD_BUCKET                = aws_s3_bucket.upload.bucket
    RESULT_BUCKET                = aws_s3_bucket.result.bucket
    USERS_TABLE                  = aws_dynamodb_table.users.name
    USAGE_LOG_TABLE              = aws_dynamodb_table.usage_log.name
    IMAGE_JOBS_TABLE             = aws_dynamodb_table.image_jobs.name
    DAILY_LIMIT                  = tostring(var.daily_limit)
    ENVIRONMENT                  = var.environment
    JOB_DOWNLOAD_EXPIRY_SECONDS  = "86400"
    POWERTOOLS_SERVICE_NAME      = "ProfilePhotoAI"
    POWERTOOLS_METRICS_NAMESPACE = "ProfilePhotoAI/Metrics"
  }
  tags = local.common_tags
}

data "aws_iam_policy_document" "image_process" {
  statement {
    sid    = "UsersAndJobsAccess"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:UpdateItem",
      "dynamodb:Query",
    ]
    resources = [
      aws_dynamodb_table.users.arn,
      aws_dynamodb_table.image_jobs.arn,
      "${aws_dynamodb_table.image_jobs.arn}/index/*",
    ]
  }

  statement {
    sid    = "ImageProcessQueueConsume"
    effect = "Allow"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:ChangeMessageVisibility",
      "sqs:GetQueueAttributes",
    ]
    resources = [aws_sqs_queue.image_process.arn]
  }

  statement {
    sid     = "UploadBucketRead"
    effect  = "Allow"
    actions = ["s3:GetObject"]
    resources = [
      "${aws_s3_bucket.upload.arn}/*",
    ]
  }

  statement {
    sid     = "ResultBucketWrite"
    effect  = "Allow"
    actions = ["s3:PutObject"]
    resources = [
      "${aws_s3_bucket.result.arn}/*",
    ]
  }

  statement {
    sid     = "BedrockInvoke"
    effect  = "Allow"
    actions = ["bedrock:InvokeModel"]
    resources = [
      "arn:aws:bedrock:${var.bedrock_region}::foundation-model/${var.bedrock_model_id}",
    ]
  }
}

module "image_process" {
  source               = "../lambda_function"
  function_name        = local.image_process_function_name
  description          = "Generate profile images with Bedrock Nova Canvas"
  handler              = "process.lambda_handler"
  timeout              = 900
  memory_size          = 2048
  source_zip           = var.lambda_artifact_paths["image_process"]
  create_inline_policy = true
  policy_json          = data.aws_iam_policy_document.image_process.json
  environment_variables = {
    RESULT_BUCKET                = aws_s3_bucket.result.bucket
    USERS_TABLE                  = aws_dynamodb_table.users.name
    IMAGE_JOBS_TABLE             = aws_dynamodb_table.image_jobs.name
    BEDROCK_REGION               = var.bedrock_region
    BEDROCK_MODEL_ID             = var.bedrock_model_id
    BEDROCK_IMAGE_TASK_TYPE      = "IMAGE_VARIATION"
    BEDROCK_IMAGE_WIDTH          = "1024"
    BEDROCK_IMAGE_HEIGHT         = "1024"
    BEDROCK_IMAGE_QUALITY        = "standard"
    BEDROCK_CFG_SCALE            = "6.5"
    BEDROCK_NUMBER_OF_IMAGES     = "1"
    BEDROCK_SIMILARITY_STRENGTH  = "0.8"
    POWERTOOLS_SERVICE_NAME      = "ProfilePhotoAI"
    POWERTOOLS_METRICS_NAMESPACE = "ProfilePhotoAI/Metrics"
  }
  tags = local.common_tags
}

resource "aws_lambda_event_source_mapping" "image_process" {
  event_source_arn = aws_sqs_queue.image_process.arn
  function_name    = module.image_process.lambda_arn
  batch_size       = 1
  enabled          = true
}

data "aws_iam_policy_document" "stats_aggregator" {
  statement {
    sid       = "LogsInsights"
    effect    = "Allow"
    actions   = ["logs:StartQuery", "logs:GetQueryResults", "logs:StopQuery", "logs:DescribeLogGroups"]
    resources = ["*"]
  }
}

module "stats_aggregator" {
  source               = "../lambda_function"
  function_name        = local.stats_aggregator_function_name
  description          = "Aggregate CloudWatch log statistics for the app"
  handler              = "stats_aggregator.lambda_handler"
  timeout              = 60
  source_zip           = var.lambda_artifact_paths["stats_aggregator"]
  create_inline_policy = true
  policy_json          = data.aws_iam_policy_document.stats_aggregator.json
  environment_variables = {
    ENVIRONMENT             = var.environment
    DISCORD_WEBHOOK_URL     = var.discord_webhook_url
    POWERTOOLS_SERVICE_NAME = "ProfilePhotoAI"
  }
  tags = local.common_tags
}

module "webhook_notifier" {
  count         = var.discord_webhook_url == "" ? 0 : 1
  source        = "../lambda_function"
  function_name = local.webhook_notifier_function_name
  description   = "Send CloudWatch alarms to Discord webhook"
  handler       = "app.lambda_handler"
  timeout       = 30
  source_zip    = var.lambda_artifact_paths["webhook_notifier"]
  environment_variables = {
    WEBHOOK_URL             = var.discord_webhook_url
    ENVIRONMENT             = var.environment
    POWERTOOLS_SERVICE_NAME = "ProfilePhotoAI"
  }
  tags = local.common_tags
}

resource "aws_sns_topic_subscription" "webhook_notifier" {
  count     = var.discord_webhook_url == "" ? 0 : 1
  topic_arn = aws_sns_topic.alarm_notifications.arn
  protocol  = "lambda"
  endpoint  = module.webhook_notifier[0].lambda_arn
}

resource "aws_lambda_permission" "allow_sns_to_invoke_webhook" {
  count         = var.discord_webhook_url == "" ? 0 : 1
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = module.webhook_notifier[0].function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.alarm_notifications.arn
}

resource "aws_cloudwatch_event_rule" "daily_report" {
  name                = "${var.project_name}-daily-report-${var.environment}"
  description         = "Run daily reporting for ProfilePhotoAI"
  schedule_expression = "cron(0 0 * * ? *)"
  tags                = local.common_tags
}

resource "aws_cloudwatch_event_target" "daily_report" {
  rule      = aws_cloudwatch_event_rule.daily_report.name
  target_id = "stats-aggregator"
  arn       = module.stats_aggregator.lambda_arn
}

resource "aws_lambda_permission" "allow_eventbridge_to_invoke_stats" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = module.stats_aggregator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_report.arn
}

resource "aws_apigatewayv2_api" "http" {
  name          = "${var.project_name}-${var.environment}"
  protocol_type = "HTTP"

  cors_configuration {
    allow_headers = ["Authorization", "Content-Type"]
    allow_methods = ["GET", "OPTIONS", "POST"]
    allow_origins = var.cors_allowed_origins
    max_age       = 3000
  }

  tags = local.common_tags
}

resource "aws_apigatewayv2_authorizer" "jwt" {
  api_id           = aws_apigatewayv2_api.http.id
  name             = "cognito-jwt"
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    audience = [aws_cognito_user_pool_client.this.id]
    issuer   = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.this.id}"
  }
}

resource "aws_apigatewayv2_integration" "file_transfer" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = module.file_transfer.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "api_manager" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = module.api_manager.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "upload" {
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "POST /upload"
  target             = "integrations/${aws_apigatewayv2_integration.file_transfer.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "healthz" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "GET /healthz"
  target    = "integrations/${aws_apigatewayv2_integration.api_manager.id}"
}

resource "aws_apigatewayv2_route" "generate" {
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "POST /generate"
  target             = "integrations/${aws_apigatewayv2_integration.api_manager.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "job" {
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /jobs/{jobId}"
  target             = "integrations/${aws_apigatewayv2_integration.api_manager.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "job_download" {
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /jobs/{jobId}/download"
  target             = "integrations/${aws_apigatewayv2_integration.api_manager.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "user_me" {
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /user/me"
  target             = "integrations/${aws_apigatewayv2_integration.api_manager.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "user_jobs" {
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "GET /user/jobs"
  target             = "integrations/${aws_apigatewayv2_integration.api_manager.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_stage" "this" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = var.environment
  auto_deploy = true
  tags        = local.common_tags
}

resource "aws_lambda_permission" "allow_http_api_file_transfer" {
  statement_id  = "AllowHttpApiInvokeFileTransfer"
  action        = "lambda:InvokeFunction"
  function_name = module.file_transfer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

resource "aws_lambda_permission" "allow_http_api_api_manager" {
  statement_id  = "AllowHttpApiInvokeApiManager"
  action        = "lambda:InvokeFunction"
  function_name = module.api_manager.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

resource "aws_cloudwatch_log_metric_filter" "nova_api_error" {
  name           = "${var.project_name}-nova-api-error-${var.environment}"
  log_group_name = module.image_process.log_group_name
  pattern        = "{ $.message = \"nova_api_error\" }"

  metric_transformation {
    name      = "NovaApiErrors"
    namespace = local.metric_namespace
    value     = "1"
  }
}

resource "aws_cloudwatch_log_metric_filter" "nova_api_slow_response" {
  name           = "${var.project_name}-nova-api-slow-${var.environment}"
  log_group_name = module.image_process.log_group_name
  pattern        = "{ $.message = \"nova_api_slow_response\" }"

  metric_transformation {
    name      = "NovaApiSlowResponses"
    namespace = local.metric_namespace
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "image_process_errors" {
  alarm_name          = "${var.project_name}-ImageProcessErrors-${var.environment}"
  alarm_description   = "Image process Lambda has invocation errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_actions       = [aws_sns_topic.alarm_notifications.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = module.image_process.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "api_manager_errors" {
  alarm_name          = "${var.project_name}-ApiManagerErrors-${var.environment}"
  alarm_description   = "API manager Lambda has invocation errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_actions       = [aws_sns_topic.alarm_notifications.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = module.api_manager.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "file_transfer_errors" {
  alarm_name          = "${var.project_name}-FileTransferErrors-${var.environment}"
  alarm_description   = "File transfer Lambda has invocation errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_actions       = [aws_sns_topic.alarm_notifications.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = module.file_transfer.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "${var.project_name}-ImageProcessDLQ-${var.environment}"
  alarm_description   = "Image processing DLQ has visible messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 0
  alarm_actions       = [aws_sns_topic.alarm_notifications.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.image_process_dlq.name
  }
}

resource "aws_cloudwatch_metric_alarm" "nova_api_errors" {
  alarm_name          = "${var.project_name}-NovaApiErrors-${var.environment}"
  alarm_description   = "Nova API returned model-level errors"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = aws_cloudwatch_log_metric_filter.nova_api_error.metric_transformation[0].name
  namespace           = local.metric_namespace
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_actions       = [aws_sns_topic.alarm_notifications.arn]
  treat_missing_data  = "notBreaching"
}

resource "aws_cloudwatch_metric_alarm" "nova_api_slow" {
  alarm_name          = "${var.project_name}-NovaApiSlowResponses-${var.environment}"
  alarm_description   = "Nova API requests are consistently slow"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = aws_cloudwatch_log_metric_filter.nova_api_slow_response.metric_transformation[0].name
  namespace           = local.metric_namespace
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_actions       = [aws_sns_topic.alarm_notifications.arn]
  treat_missing_data  = "notBreaching"
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_5xx" {
  alarm_name          = "${var.project_name}-ApiGateway5xx-${var.environment}"
  alarm_description   = "HTTP API returns 5xx responses"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "5xx"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_actions       = [aws_sns_topic.alarm_notifications.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiId = aws_apigatewayv2_api.http.id
    Stage = aws_apigatewayv2_stage.this.name
  }
}
