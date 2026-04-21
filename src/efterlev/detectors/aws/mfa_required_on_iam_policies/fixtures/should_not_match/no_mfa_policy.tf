resource "aws_iam_policy" "admin_no_mfa" {
  name = "admin-no-mfa"
  policy = <<-EOT
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": "*",
          "Resource": "*"
        }
      ]
    }
  EOT
}
