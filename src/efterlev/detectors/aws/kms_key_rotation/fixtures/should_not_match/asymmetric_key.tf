resource "aws_kms_key" "signing" {
  description              = "Asymmetric RSA signing key"
  key_usage                = "SIGN_VERIFY"
  customer_master_key_spec = "RSA_4096"
  deletion_window_in_days  = 30
}
