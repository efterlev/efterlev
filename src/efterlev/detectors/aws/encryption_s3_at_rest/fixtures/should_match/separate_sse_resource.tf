resource "aws_s3_bucket" "payloads" {
  bucket = "payloads-prod"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "payloads_sse" {
  bucket = aws_s3_bucket.payloads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}
