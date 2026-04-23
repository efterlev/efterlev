resource "aws_iam_user" "legacy" {
  name = "legacy-runner"
}

resource "aws_iam_access_key" "legacy" {
  user    = aws_iam_user.legacy.name
  status  = "Inactive"
  pgp_key = "keybase:somekey"
}
