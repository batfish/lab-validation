##### vpc vars
variable "region" {
  description = "region"
  type        = string
  default     = "us-east-1"
}
variable "profile" {
  description = "profile"
  type        = string
  default     = "SandboxAdmin"
}
variable "cidr" {
  description = "The CIDR block for the VPC"
  type        = string
  default     = "10.1.0.0/16"
}
variable "jump_cidr" {
  description = "jump subnet"
  type        = string
  default     = "10.1.100.0/24"
}
variable "public_cidr_az_1" {
  description = "public subnet az 1"
  type        = string
  default     = "10.1.1.0/24"
}
variable "public_cidr_az_2" {
  description = "public subnet az 2"
  type        = string
  default     = "10.1.2.0/24"
}
variable "private_cidr_az_1" {
  description = "private subnet az 1"
  type        = string
  default     = "10.1.101.0/24"
}
variable "private_cidr_az_2" {
  description = "private subnet az 2"
  type        = string
  default     = "10.1.102.0/24"
}
variable "private_cidr_az_3" {
  description = "private subnet az 3"
  type        = string
  default     = "10.1.103.0/24"
}
variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {
    Terraform   = "true"
    Environment = "dev"
  }
}
variable "any_subnet" {
  default = "0.0.0.0/0"
}
variable "rfc_1918_10" {
  default = "10.0.0.0/8"
}
variable "rfc_1918_172" {
  default = "172.16.0.0/20"
}
variable "rfc_1918_192" {
  default = "192.168.0.0/16"
}
variable "jump_host" {
  description = "jump host"
  type        = string
  default     = "10.1.100.100/32"
}
variable "jump_host_private_ip" {
  description = "jump host private ip"
  type        = string
  default     = "10.1.100.100"
}

##### ec2 vars
variable "ami" {
  description = "ID of AMI to use for the instance. Default is us-east-1 amazon linux"
  type        = string
  default     = "ami-0fc61db8544a617ed"
}
variable "instance_type" {
  description = "type for aws EC2 instance"
  default     = "t2.micro"
}
##### change ssh pub key path as appropriate
variable "public_key_path" {
  description = "Public key path"
  default = "~/.ssh/id_rsa.pub"
}
variable "create_web_server" {
  description = "web server script"
  default = "./create_web_server.sh"
}
variable "update_server" {
  description = "update server and install nmap and nc"
  default = "./update_server.sh"
}

##### data sources
data "aws_availability_zones" "az" {
  state = "available"
}
data "aws_caller_identity" "current" {}
