#################### common ####################
variable "region-2" {
  description = "region 2"
  default     = "us-west-1"
}
variable "california-ec2-instance-ami" {
  description = "AMI for aws EC2 instance"
  default     = "ami-09a7fe78668f1e2c0"
}
variable "california-ec2-instance-type"  {
  description = "type for aws EC2 instance"
  default     = "t2.micro"
}
#################### vpc-hr-west ####################
variable "vpc-hr-west" {
  description = "VPC Name"
  default     = "vpc-hr-west"
}
variable "cidr-hr-west" {
  description = "CIDR block for the VPC"
  default     = "10.3.0.0/16"
}
variable "subnet-web-hr-west" {
  description = "subnet web"
  default     = "10.3.1.0/24"
}
variable "subnet-data-hr-west" {
  description = "subnet db"
  default     = "10.3.101.0/24"
}
variable "subnet-public-hr-west" {
  description = "subnet public"
  default     = "10.3.201.0/24"
}
variable "subnet-tgw-hr-west" {
  description = "subnet tgw"
  default     = "10.3.250.0/28"
}
#################### vpc-it-west ####################
variable "vpc-it-west" {
  description = "VPC Name"
  default     = "vpc-it-west"
}
variable "cidr-it-west" {
  description = "CIDR block for the VPC"
  default     = "10.4.0.0/16"
}
variable "subnet-jump-it-west" {
  description = "subnet jump"
  default     = "10.4.1.0/24"
}
variable "subnet-tgw-it-west" {
  description = "subnet tgw"
  default     = "10.4.250.0/28"
}
