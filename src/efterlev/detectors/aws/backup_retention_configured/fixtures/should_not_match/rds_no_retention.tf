resource "aws_db_instance" "scratch" {
  identifier              = "scratch"
  engine                  = "postgres"
  instance_class          = "db.t3.micro"
  allocated_storage       = 20
  backup_retention_period = 0
  skip_final_snapshot     = true
}
