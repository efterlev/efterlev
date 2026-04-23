resource "aws_iam_account_password_policy" "weak" {
  minimum_password_length      = 8
  require_uppercase_characters = true
  require_lowercase_characters = true
  require_numbers              = false
  require_symbols              = false
  max_password_age             = 120
  password_reuse_prevention    = 4
}
