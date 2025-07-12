#################### common ####################
# change profile as necessary. Generally profile is "default"
variable "region-1" {
  description = "region 1"
  default     = "us-east-1"
}
variable "virginia-ec2-instance-ami" {
  description = "AMI for aws EC2 instance"
  default     = "ami-0a887e401f7654935"
}
variable "virginia-ec2-instance-type"  {
  description = "type for aws EC2 instance"
  default     = "t2.micro"
}

#################### vpc-hr-east ####################
variable "vpc-hr-east" {
  description = "VPC Name"
  default     = "vpc-hr-east"
}
variable "cidr-hr-east" {
  description = "CIDR block for the VPC"
  default     = "10.1.0.0/16"
}
variable "subnet-web-hr-east" {
  description = "subnet web"
  default     = "10.1.1.0/24"
}
variable "subnet-db-hr-east" {
  description = "subnet db"
  default     = "10.1.101.0/24"
}
variable "subnet-public-hr-east" {
  description = "subnet public"
  default     = "10.1.201.0/24"
}
variable "subnet-tgw-hr-east" {
  description = "subnet tgw"
  default     = "10.1.250.0/28"
}
#################### vpc-fin-east ####################
variable "vpc-fin-east" {
  description = "VPC Name"
  default     = "vpc-fin-east"
}
variable "cidr-fin-east" {
  description = "CIDR block for the VPC"
  default     = "10.2.0.0/16"
}
variable "subnet-expenses-fin-east" {
  description = "subnet web"
  default     = "10.2.1.0/24"
}
variable "subnet-db-fin-east" {
  description = "subnet db"
  default     = "10.2.101.0/24"
}
variable "subnet-tgw-fin-east" {
  description = "subnet tgw"
  default     = "10.2.250.0/28"
}
