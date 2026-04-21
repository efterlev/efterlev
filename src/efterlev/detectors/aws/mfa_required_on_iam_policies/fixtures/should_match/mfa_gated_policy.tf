resource "aws_iam_policy" "admin_with_mfa" {
  name = "admin-with-mfa"
  policy = <<-EOT
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": "*",
          "Resource": "*",
          "Condition": {
            "Bool": {"aws:MultiFactorAuthPresent": "true"}
          }
        }
      ]
    }
  EOT
}
