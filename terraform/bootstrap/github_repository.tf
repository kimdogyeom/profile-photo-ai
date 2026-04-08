locals {
  github_environments = {
    dev = {
      name             = var.github_dev_environment_name
      domain_name      = lookup(var.github_environment_domain_names, "dev", "")
      hosted_zone_name = lookup(var.github_environment_hosted_zone_names, "dev", "")
      role_arn         = aws_iam_role.github_actions["dev"].arn
    }
    prod = {
      name             = var.github_prod_environment_name
      domain_name      = lookup(var.github_environment_domain_names, "prod", "")
      hosted_zone_name = lookup(var.github_environment_hosted_zone_names, "prod", "")
      role_arn         = aws_iam_role.github_actions["prod"].arn
    }
  }

  github_environment_variables = merge(
    {
      for environment, cfg in local.github_environments :
      "${environment}:AWS_ROLE_TO_ASSUME_${upper(environment)}" => {
        environment = cfg.name
        name        = "AWS_ROLE_TO_ASSUME_${upper(environment)}"
        value       = cfg.role_arn
      }
    },
    {
      for environment, cfg in local.github_environments :
      "${environment}:TF_VAR_DOMAIN_NAME" => {
        environment = cfg.name
        name        = "TF_VAR_DOMAIN_NAME"
        value       = cfg.domain_name
      }
    },
    {
      for environment, cfg in local.github_environments :
      "${environment}:TF_VAR_HOSTED_ZONE_NAME" => {
        environment = cfg.name
        name        = "TF_VAR_HOSTED_ZONE_NAME"
        value       = cfg.hosted_zone_name
      }
    }
  )
}

resource "github_repository_environment" "this" {
  for_each = local.github_environments

  repository  = var.github_repo_name
  environment = each.value.name
}

resource "github_actions_environment_variable" "this" {
  for_each = local.github_environment_variables

  repository    = var.github_repo_name
  environment   = each.value.environment
  variable_name = each.value.name
  value         = each.value.value

  depends_on = [github_repository_environment.this]
}
