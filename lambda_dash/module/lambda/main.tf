resource "aws_iam_role" "lambda_execution_role" {
  name = "lambda_execution_role_${var.env}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_iam_role_policy" "lambda_permissions_policy" {
  name   = "lambda_permissions_policy_${var.env}"
  role   = aws_iam_role.lambda_execution_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "elasticloadbalancing:DescribeLoadBalancers",
          "elasticloadbalancing:DescribeTargetGroups",
          "cloudwatch:PutMetricData"
        ],
        Effect   = "Allow",
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_function" "create_dashboard_function" {
  filename         = "index.zip"
  function_name    = "CreateDashboardFunction_${var.env}"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "index.lambda_handler"
  source_code_hash = filebase64sha256("index.zip")
  runtime          = "python3.8"
  environment {
    variables = {
      ENV                 = var.env
      CUSTOMER_NAME       = var.customer_name
      RDS_NAMES           = var.rds_names
      ECS_CLUSTERS        = var.ecs_clusters
      REDIS_NAMES         = var.redis_names
      LOAD_BALANCER_NAMES = var.load_balancer_names
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}
