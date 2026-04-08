data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

locals {
  github_repo_full_name = "${var.github_repo_owner}/${var.github_repo_name}"

  github_environment_subjects = {
    dev  = "repo:${local.github_repo_full_name}:environment:${var.github_dev_environment_name}"
    prod = "repo:${local.github_repo_full_name}:environment:${var.github_prod_environment_name}"
  }

  github_actions_role_names = {
    dev  = var.github_actions_dev_role_name
    prod = var.github_actions_prod_role_name
  }

  app_bucket_names = flatten([
    for environment in keys(local.github_environment_subjects) : [
      "${var.project_name}-uploads-raw-${environment}",
      "${var.project_name}-results-final-${environment}",
      "${var.project_name}-logs-archive-${environment}",
      "${var.project_name}-frontend-${environment}",
    ]
  ])

  app_bucket_arns = [
    for bucket_name in local.app_bucket_names : "arn:${data.aws_partition.current.partition}:s3:::${bucket_name}"
  ]

  app_bucket_object_arns = [
    for bucket_name in local.app_bucket_names : "arn:${data.aws_partition.current.partition}:s3:::${bucket_name}/*"
  ]

  app_table_names = flatten([
    for environment in keys(local.github_environment_subjects) : [
      "${var.project_name}-users-${environment}",
      "${var.project_name}-usage-log-${environment}",
      "${var.project_name}-image-jobs-${environment}",
    ]
  ])

  app_table_arns = [
    for table_name in local.app_table_names : "arn:${data.aws_partition.current.partition}:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${table_name}"
  ]

  app_table_index_arns = [
    for table_name in local.app_table_names : "arn:${data.aws_partition.current.partition}:dynamodb:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${table_name}/index/*"
  ]

  app_queue_names = flatten([
    for environment in keys(local.github_environment_subjects) : [
      "${var.project_name}-image-process-${environment}",
      "${var.project_name}-image-process-dlq-${environment}",
    ]
  ])

  app_queue_arns = [
    for queue_name in local.app_queue_names : "arn:${data.aws_partition.current.partition}:sqs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:${queue_name}"
  ]

  app_topic_arns = [
    for environment in keys(local.github_environment_subjects) : "arn:${data.aws_partition.current.partition}:sns:${var.aws_region}:${data.aws_caller_identity.current.account_id}:${var.project_name}-alarm-notifications-${environment}"
  ]

  app_lambda_function_arns = [
    for environment in keys(local.github_environment_subjects) : "arn:${data.aws_partition.current.partition}:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${var.project_name}-*-${environment}"
  ]

  app_log_group_arns = [
    for environment in keys(local.github_environment_subjects) : "arn:${data.aws_partition.current.partition}:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.project_name}-*-${environment}:*"
  ]

  app_event_rule_arns = [
    for environment in keys(local.github_environment_subjects) : "arn:${data.aws_partition.current.partition}:events:${var.aws_region}:${data.aws_caller_identity.current.account_id}:rule/${var.project_name}-daily-report-${environment}"
  ]

  app_alarm_arns = [
    for environment in keys(local.github_environment_subjects) : "arn:${data.aws_partition.current.partition}:cloudwatch:${var.aws_region}:${data.aws_caller_identity.current.account_id}:alarm:${var.project_name}-*-${environment}"
  ]

  app_role_arns = [
    for environment in keys(local.github_environment_subjects) : "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:role/${var.project_name}-*-${environment}*"
  ]
}

resource "aws_iam_openid_connect_provider" "github_actions" {
  url            = var.github_oidc_url
  client_id_list = var.github_oidc_client_ids
}

data "aws_iam_policy_document" "github_actions_assume_role" {
  for_each = local.github_environment_subjects

  statement {
    effect = "Allow"

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github_actions.arn]
    }

    actions = [
      "sts:AssumeRoleWithWebIdentity",
    ]

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = [each.value]
    }
  }
}

resource "aws_iam_role" "github_actions" {
  for_each = local.github_environment_subjects

  name                 = local.github_actions_role_names[each.key]
  assume_role_policy   = data.aws_iam_policy_document.github_actions_assume_role[each.key].json
  description          = "GitHub Actions deploy role for ${each.key}"
  max_session_duration = 7200

  tags = {
    Project     = var.project_name
    ManagedBy   = "terraform"
    Environment = each.key
  }
}

data "aws_iam_policy_document" "github_actions_permissions" {
  statement {
    sid    = "TerraformStateBucketAccess"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
      "s3:GetBucketVersioning",
      "s3:PutBucketVersioning",
      "s3:GetBucketEncryption",
      "s3:PutBucketEncryption",
      "s3:GetBucketPublicAccessBlock",
      "s3:PutBucketPublicAccessBlock",
      "s3:GetBucketPolicy",
      "s3:PutBucketPolicy",
      "s3:DeleteBucketPolicy",
      "s3:GetBucketTagging",
      "s3:PutBucketTagging",
      "s3:GetLifecycleConfiguration",
      "s3:PutLifecycleConfiguration",
      "s3:DeleteLifecycleConfiguration",
    ]
    resources = [aws_s3_bucket.tf_state.arn]
  }

  statement {
    sid    = "TerraformStateObjectAccess"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = ["${aws_s3_bucket.tf_state.arn}/*"]
  }

  statement {
    sid    = "CreateProjectBuckets"
    effect = "Allow"
    actions = [
      "s3:CreateBucket",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ManageProjectBuckets"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
      "s3:GetBucketVersioning",
      "s3:PutBucketVersioning",
      "s3:GetBucketEncryption",
      "s3:PutBucketEncryption",
      "s3:GetBucketPublicAccessBlock",
      "s3:PutBucketPublicAccessBlock",
      "s3:GetBucketPolicy",
      "s3:PutBucketPolicy",
      "s3:DeleteBucketPolicy",
      "s3:GetBucketCors",
      "s3:PutBucketCors",
      "s3:GetLifecycleConfiguration",
      "s3:PutLifecycleConfiguration",
      "s3:DeleteLifecycleConfiguration",
      "s3:GetBucketTagging",
      "s3:PutBucketTagging",
      "s3:DeleteBucket",
    ]
    resources = local.app_bucket_arns
  }

  statement {
    sid    = "ManageProjectBucketObjects"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:GetObjectTagging",
      "s3:PutObjectTagging",
      "s3:DeleteObjectTagging",
      "s3:AbortMultipartUpload",
    ]
    resources = local.app_bucket_object_arns
  }

  statement {
    sid    = "CreateAndManageDynamoDbTables"
    effect = "Allow"
    actions = [
      "dynamodb:CreateTable",
      "dynamodb:DeleteTable",
      "dynamodb:DescribeTable",
      "dynamodb:UpdateTable",
      "dynamodb:TagResource",
      "dynamodb:UntagResource",
      "dynamodb:ListTagsOfResource",
      "dynamodb:DescribeContinuousBackups",
      "dynamodb:UpdateTimeToLive",
      "dynamodb:DescribeTimeToLive",
      "dynamodb:DescribeTableReplicaAutoScaling",
      "dynamodb:UpdateTableReplicaAutoScaling",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ManageDynamoDbTables"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:DescribeTable",
      "dynamodb:DescribeContinuousBackups",
      "dynamodb:UpdateTimeToLive",
      "dynamodb:DescribeTimeToLive",
    ]
    resources = concat(local.app_table_arns, local.app_table_index_arns)
  }

  statement {
    sid    = "CreateSqsQueues"
    effect = "Allow"
    actions = [
      "sqs:CreateQueue",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ManageSqsQueues"
    effect = "Allow"
    actions = [
      "sqs:GetQueueUrl",
      "sqs:GetQueueAttributes",
      "sqs:SetQueueAttributes",
      "sqs:TagQueue",
      "sqs:UntagQueue",
      "sqs:DeleteQueue",
    ]
    resources = local.app_queue_arns
  }

  statement {
    sid    = "CreateSnsTopics"
    effect = "Allow"
    actions = [
      "sns:CreateTopic",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ManageSnsTopics"
    effect = "Allow"
    actions = [
      "sns:DeleteTopic",
      "sns:GetTopicAttributes",
      "sns:SetTopicAttributes",
      "sns:TagResource",
      "sns:UntagResource",
      "sns:Subscribe",
      "sns:Unsubscribe",
      "sns:ListSubscriptionsByTopic",
    ]
    resources = local.app_topic_arns
  }

  statement {
    sid    = "CreateLambdaFunctions"
    effect = "Allow"
    actions = [
      "lambda:CreateFunction",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ManageLambdaFunctions"
    effect = "Allow"
    actions = [
      "lambda:DeleteFunction",
      "lambda:GetFunction",
      "lambda:GetFunctionConfiguration",
      "lambda:UpdateFunctionCode",
      "lambda:UpdateFunctionConfiguration",
      "lambda:PublishVersion",
      "lambda:CreateAlias",
      "lambda:UpdateAlias",
      "lambda:DeleteAlias",
      "lambda:TagResource",
      "lambda:UntagResource",
      "lambda:GetPolicy",
      "lambda:AddPermission",
      "lambda:RemovePermission",
      "lambda:ListVersionsByFunction",
    ]
    resources = local.app_lambda_function_arns
  }

  statement {
    sid    = "ManageLambdaEventSourceMappings"
    effect = "Allow"
    actions = [
      "lambda:CreateEventSourceMapping",
      "lambda:UpdateEventSourceMapping",
      "lambda:DeleteEventSourceMapping",
      "lambda:GetEventSourceMapping",
      "lambda:ListEventSourceMappings",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "CreateIamRoles"
    effect = "Allow"
    actions = [
      "iam:CreateRole",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ManageIamRoles"
    effect = "Allow"
    actions = [
      "iam:DeleteRole",
      "iam:GetRole",
      "iam:ListRolePolicies",
      "iam:ListAttachedRolePolicies",
      "iam:PutRolePolicy",
      "iam:DeleteRolePolicy",
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
      "iam:TagRole",
      "iam:UntagRole",
    ]
    resources = local.app_role_arns
  }

  statement {
    sid    = "PassLambdaRoles"
    effect = "Allow"
    actions = [
      "iam:PassRole",
    ]
    resources = local.app_role_arns
    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["lambda.amazonaws.com"]
    }
  }

  statement {
    sid    = "ManageCloudWatchLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:DeleteLogGroup",
      "logs:PutRetentionPolicy",
      "logs:DeleteRetentionPolicy",
      "logs:PutMetricFilter",
      "logs:DeleteMetricFilter",
      "logs:DescribeLogGroups",
      "logs:DescribeMetricFilters",
      "logs:TagLogGroup",
      "logs:UntagLogGroup",
    ]
    resources = local.app_log_group_arns
  }

  statement {
    sid    = "ManageCloudWatchAlarms"
    effect = "Allow"
    actions = [
      "cloudwatch:PutMetricAlarm",
      "cloudwatch:DeleteAlarms",
      "cloudwatch:DescribeAlarms",
      "cloudwatch:EnableAlarmActions",
      "cloudwatch:DisableAlarmActions",
    ]
    resources = local.app_alarm_arns
  }

  statement {
    sid    = "ManageEventBridgeRules"
    effect = "Allow"
    actions = [
      "events:PutRule",
      "events:DeleteRule",
      "events:DescribeRule",
      "events:PutTargets",
      "events:RemoveTargets",
      "events:ListTargetsByRule",
      "events:TagResource",
      "events:UntagResource",
    ]
    resources = local.app_event_rule_arns
  }

  statement {
    sid    = "ManageApiGatewayV2"
    effect = "Allow"
    actions = [
      "apigateway:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ManageCognito"
    effect = "Allow"
    actions = [
      "cognito-idp:*",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ManageCloudFront"
    effect = "Allow"
    actions = [
      "cloudfront:CreateDistribution",
      "cloudfront:DeleteDistribution",
      "cloudfront:GetDistribution",
      "cloudfront:GetDistributionConfig",
      "cloudfront:UpdateDistribution",
      "cloudfront:CreateInvalidation",
      "cloudfront:GetCachePolicy",
      "cloudfront:ListCachePolicies",
      "cloudfront:ListDistributions",
      "cloudfront:TagResource",
      "cloudfront:UntagResource",
      "cloudfront:ListTagsForResource",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ManageRoute53"
    effect = "Allow"
    actions = [
      "route53:ChangeResourceRecordSets",
      "route53:GetHostedZone",
      "route53:ListHostedZones",
      "route53:ListHostedZonesByName",
      "route53:ListResourceRecordSets",
      "route53:ListTagsForResource",
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ReadIdentity"
    effect = "Allow"
    actions = [
      "sts:GetCallerIdentity",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "github_actions" {
  for_each = local.github_environment_subjects

  name   = "${var.project_name}-github-actions-${each.key}-permissions"
  role   = aws_iam_role.github_actions[each.key].id
  policy = data.aws_iam_policy_document.github_actions_permissions.json
}

output "github_actions_oidc_provider_arn" {
  value = aws_iam_openid_connect_provider.github_actions.arn
}

output "github_actions_role_arns" {
  value = {
    for environment, role in aws_iam_role.github_actions : environment => role.arn
  }
}

output "github_actions_dev_role_arn" {
  value = aws_iam_role.github_actions["dev"].arn
}

output "github_actions_prod_role_arn" {
  value = aws_iam_role.github_actions["prod"].arn
}
