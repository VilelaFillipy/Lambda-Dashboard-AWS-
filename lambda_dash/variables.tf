variable "env" {
  description = "Environment name"
  type        = string
}

variable "customer_name" {
  description = "Customer name"
  type        = string
}

variable "rds_names" {
  description = "Comma-separated list of RDS instance names"
  type        = string
}

variable "ecs_clusters" {
  description = "Comma-separated list of ECS cluster names"
  type        = string
}

variable "redis_names" {
  description = "Comma-separated list of Redis instance names"
  type        = string
}

variable "load_balancer_names" {
  description = "Comma-separated list of Load Balancer names"
  type        = string
}