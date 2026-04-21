resource "aws_s3_bucket" "audit_logs" {
  bucket = "audit-logs-prod"

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm     = "aws:kms"
        kms_master_key_id = "arn:aws:kms:us-east-1:123456789012:key/abc"
      }
    }
  }
}
