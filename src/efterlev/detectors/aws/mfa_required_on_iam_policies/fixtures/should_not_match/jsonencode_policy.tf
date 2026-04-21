# `jsonencode(...)` renders as a string expression python-hcl2 cannot
# statically resolve; the detector emits `mfa_required="unparseable"`.
# Included here to lock in the "can't decide" path as a tested case.
resource "aws_iam_policy" "encoded" {
  name = "encoded"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "*"
        Resource = "*"
      }
    ]
  })
}
