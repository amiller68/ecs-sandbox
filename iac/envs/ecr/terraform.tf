terraform {
  backend "s3" {
    bucket         = "ecs-sandbox-tf-state"
    key            = "ecr/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "ecs-sandbox-tf-state-lock"
  }
}
