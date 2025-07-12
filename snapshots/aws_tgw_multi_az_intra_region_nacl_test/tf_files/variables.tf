##### vpc common vars
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
  description = "jump host ip"
  type        = string
  default     = "10.1.100.100"
}

##### vpc prod vars
variable "prod_cidr" {
  description = "The CIDR block for the VPC"
  type        = string
  default     = "10.1.0.0/16"
}
variable "prod_jump_cidr" {
  description = "jump subnet"
  type        = string
  default     = "10.1.100.0/24"
}
variable "prod_pub_cidr" {
  description = "public subnet"
  type        = string
  default     = "10.1.1.0/24"
}
variable "prod_priv_cidr_az1" {
  description = "private subnet"
  type        = string
  default     = "10.1.101.0/24"
}
variable "prod_priv_cidr_az2" {
  description = "private subnet"
  type        = string
  default     = "10.1.102.0/24"
}
variable "prod_tgw_cidr_az1" {
  description = "private subnet"
  type        = string
  default     = "10.1.201.0/24"
}
variable "prod_tgw_cidr_az2" {
  description = "private subnet"
  type        = string
  default     = "10.1.202.0/24"
}
variable "prod_tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {
    Terraform   = "true"
    Environment = "prod"
  }
}

##### vpc dev vars
variable "dev_cidr" {
  description = "The CIDR block for the VPC"
  type        = string
  default     = "10.2.0.0/16"
}
variable "dev_pub_cidr" {
  description = "public subnet"
  type        = string
  default     = "10.2.1.0/24"
}
variable "dev_priv_cidr_az1" {
  description = "private subnet"
  type        = string
  default     = "10.2.101.0/24"
}
variable "dev_priv_cidr_az2" {
  description = "private subnet"
  type        = string
  default     = "10.2.102.0/24"
}
variable "dev_tgw_cidr_az1" {
  description = "private subnet"
  type        = string
  default     = "10.2.201.0/24"
}
variable "dev_tgw_cidr_az2" {
  description = "private subnet"
  type        = string
  default     = "10.2.202.0/24"
}
variable "dev_tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {
    Terraform   = "true"
    Environment = "dev"
  }
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
# change ssh pub key path as appropriate
variable "pub_key_path" {
  description = "public key path"
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
