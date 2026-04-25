output "api_base_url" {
  value = "${aws_apigatewayv2_api.http.api_endpoint}/${aws_apigatewayv2_stage.this.name}"
}

output "frontend_bucket_name" {
  value = module.frontend_site.bucket_name
}

output "frontend_distribution_id" {
  value = module.frontend_site.distribution_id
}

output "frontend_url" {
  value = module.frontend_site.frontend_url
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.this.id
}

output "cognito_user_pool_client_id" {
  value = aws_cognito_user_pool_client.this.id
}

output "cognito_domain" {
  value = "${aws_cognito_user_pool_domain.this.domain}.auth.${var.aws_region}.amazoncognito.com"
}

output "upload_bucket_name" {
  value = aws_s3_bucket.upload.bucket
}

output "result_bucket_name" {
  value = aws_s3_bucket.result.bucket
}
