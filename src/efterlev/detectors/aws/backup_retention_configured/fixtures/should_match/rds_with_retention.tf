resource "aws_db_instance" "primary" {
  identifier              = "app-primary"
  engine                  = "postgres"
  instance_class          = "db.t3.micro"
  allocated_storage       = 20
  backup_retention_period = 7
  skip_final_snapshot     = false
}
