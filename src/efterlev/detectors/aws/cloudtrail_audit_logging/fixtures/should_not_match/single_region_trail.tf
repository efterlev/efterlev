resource "aws_cloudtrail" "single" {
  name                  = "single-region"
  s3_bucket_name        = "audit-logs-bucket"
  is_multi_region_trail = false
}
