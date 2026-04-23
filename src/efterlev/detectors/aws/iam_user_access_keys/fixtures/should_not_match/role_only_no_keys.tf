resource "aws_iam_role" "app_task" {
  name               = "app-task"
  assume_role_policy = "{}"
}

resource "aws_iam_user" "alice" {
  name = "alice"
}
