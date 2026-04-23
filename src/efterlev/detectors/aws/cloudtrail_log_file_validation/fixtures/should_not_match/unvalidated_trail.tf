resource "aws_cloudtrail" "dev" {
  name                  = "dev-trail"
  s3_bucket_name        = "dev-audit-logs"
  is_multi_region_trail = false
}
