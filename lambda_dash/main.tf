
module "lambda" {
  source = "./module/lambda"

  env                 = var.env
  customer_name       = var.customer_name
  rds_names           = var.rds_names
  ecs_clusters        = var.ecs_clusters
  redis_names         = var.redis_names
  load_balancer_names = var.load_balancer_names
}
