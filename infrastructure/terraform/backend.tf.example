terraform {
  backend "s3" {
    bucket         = "tableno-terraform-state"
    key            = "aws-pre/terraform.tfstate"
    region         = "ap-northeast-1"
    dynamodb_table = "tableno-terraform-locks"
    encrypt        = true
  }
}
