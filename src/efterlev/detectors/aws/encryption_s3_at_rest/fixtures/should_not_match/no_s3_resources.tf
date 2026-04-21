resource "aws_iam_user" "ops" {
  name = "ops-user"
}

variable "region" {
  default = "us-east-1"
}
