resource "aws_s3_bucket_versioning" "misconfig" {
  bucket = "misconfigured-bucket"
  versioning_configuration {
    status = "Suspended"
  }
}
