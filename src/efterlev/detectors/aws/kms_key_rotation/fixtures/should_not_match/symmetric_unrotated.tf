resource "aws_kms_key" "legacy" {
  description             = "Legacy symmetric key without rotation"
  deletion_window_in_days = 7
}
