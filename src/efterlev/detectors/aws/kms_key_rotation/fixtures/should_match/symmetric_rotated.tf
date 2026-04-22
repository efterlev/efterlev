resource "aws_kms_key" "app_data" {
  description             = "Application-data encryption key"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}
