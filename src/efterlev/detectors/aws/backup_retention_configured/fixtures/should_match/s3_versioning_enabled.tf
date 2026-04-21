resource "aws_s3_bucket_versioning" "logs" {
  bucket = "audit-logs-bucket"
  versioning_configuration {
    status = "Enabled"
  }
}
