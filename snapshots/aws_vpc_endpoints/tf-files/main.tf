##################################### VPC bat ###################################
#################### common ####################
variable "vpc_region_virginia" {
  description = "VPC Region"
  default     = "us-east-1"
}
# change profile as necessary. Generally profile is "default"
variable "profile" {
  description = "account profile"
  default     = "SandboxAdmin"
}
# change ssh pub key path as appropriate
variable "public_key_path" {
  description = "Public key path"
  default = "~/.ssh/id_rsa.pub"
}
variable "instance_ami_a41_virginia" {
  description = "AMI for aws EC2 instance"
  default     = "ami-0323c3dd2da7fb37d"
}
variable "instance_type_t2_micro_virginia" {
  description = "type for aws EC2 instance"
  default     = "t2.micro"
}
variable "update-server" {
  description = "update server and install nmap and nc"
  default = "update-server.sh"
}
data "aws_caller_identity" "requester_account" {}
output "account_id_requester_account" {
  value = data.aws_caller_identity.requester_account.account_id
}

#################### bat ####################
# `bat` is the vpc keyword being used for tagging in all resources belongs to this vpc.
# replace `bat` with your prefered name.

variable "bat" {
  description = "VPC Name"
  default     = "bat"
}
variable "bat_cidr" {
  description = "CIDR block for the VPC"
  default     = "10.1.0.0/16"
}
variable "bat_public_subnet" {
  description = "public subnet"
  default     = "10.1.1.0/24"
}
variable "bat_nat_subnet" {
  description = "nat subnet"
  default     = "10.1.2.0/24"
}
variable "bat_private_subnet" {
  description = "nat subnet"
  default     = "10.1.3.0/24"
}
data "aws_availability_zones" "az_virginia" {
  state = "available"
}

#################### Provider Config ####################
provider "aws" {
  profile = var.profile
  region  = var.vpc_region_virginia
}
# Use existing ssh key pair
resource "aws_key_pair" "ec2key" {
  key_name = "publicKey"
  public_key = file(var.public_key_path)
}

#################### vpc ####################
# Define VPC
resource "aws_vpc" "bat" {
  cidr_block = var.bat_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = var.bat
  }
}

############# Subnets #############
# Define public subnet
resource "aws_subnet" "bat_public_subnet" {
  vpc_id     = aws_vpc.bat.id
  cidr_block = var.bat_public_subnet
  map_public_ip_on_launch = "true"
  availability_zone = data.aws_availability_zones.az_virginia.names[0]
  tags = {
    Name = format("%s_%s", var.bat, var.bat_public_subnet)
  }
}
# Define nat subnet
resource "aws_subnet" "bat_nat_subnet" {
  vpc_id     = aws_vpc.bat.id
  cidr_block = var.bat_nat_subnet
  availability_zone = data.aws_availability_zones.az_virginia.names[0]
  tags = {
    Name = format("%s_%s", var.bat, var.bat_nat_subnet)
  }
}
# Define private subnet
resource "aws_subnet" "bat_private_subnet" {
  vpc_id     = aws_vpc.bat.id
  cidr_block = var.bat_private_subnet
  availability_zone = data.aws_availability_zones.az_virginia.names[0]
  tags = {
    Name = format("%s_%s", var.bat, var.bat_private_subnet)
  }
}
############# gateways #############
# Define internet gateway
resource "aws_internet_gateway" "bat_igw" {
  vpc_id = aws_vpc.bat.id
  tags = {
    Name = var.bat
  }
}
# Define elastic ip for ngw
resource "aws_eip" "eip_ngw_bat" {
  vpc = true
    tags = {
    Name = format("eip_ngw_bat")
  }
}
# Define ngw
resource "aws_nat_gateway" "ngw_bat" {
  allocation_id = aws_eip.eip_ngw_bat.id
  subnet_id     = aws_subnet.bat_public_subnet.id
  depends_on = [aws_internet_gateway.bat_igw]
    tags = {
    Name = format("ngw_bat")
  }
}
#################### route tables ####################
# Define route table  - igw
resource "aws_route_table" "bat_rtb_igw" {
  vpc_id = aws_vpc.bat.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.bat_igw.id
  }
  tags = {
    Name = format("%s-igw", var.bat)
  }
}
# associate igw route table to the public subnet
resource "aws_route_table_association" "bat_rtb_asctn_public" {
  route_table_id = aws_route_table.bat_rtb_igw.id
  subnet_id      = aws_subnet.bat_public_subnet.id
}

# Define route table  - ngw
resource "aws_route_table" "bat_rtb_ngw" {
  vpc_id = aws_vpc.bat.id
  route {
    cidr_block = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.ngw_bat.id
  }
  tags = {
    Name = format("bat_rtb_ngw")
  }
}
# associate pirvate route table to the nat subnet
resource "aws_route_table_association" "bat_rtb_asctn_nat" {
  route_table_id = aws_route_table.bat_rtb_ngw.id
  subnet_id      = aws_subnet.bat_nat_subnet.id
}

# Define route table  - private
resource "aws_route_table" "bat_rtb_private" {
  vpc_id = aws_vpc.bat.id
  tags = {
    Name = format("%s-private", var.bat)
  }
}
# associate pirvate route table to the private subnet
resource "aws_route_table_association" "bat_rtb_asctn_private" {
  route_table_id = aws_route_table.bat_rtb_private.id
  subnet_id      = aws_subnet.bat_private_subnet.id
}
############# security-group #############
# Define security-group
resource "aws_security_group" "bat_sg" {
  name = "bat_sg"
  vpc_id = aws_vpc.bat.id
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all"
  }
  tags = {
    Name =  format("%s-general", var.bat)
  }
}
############# NACL #############
resource "aws_network_acl" "bat_nacl" {
  vpc_id = aws_vpc.bat.id
  subnet_ids = [
    aws_subnet.bat_public_subnet.id,
    aws_subnet.bat_nat_subnet.id,
    aws_subnet.bat_private_subnet.id
  ]
  ingress {
    protocol   = "-1"
    rule_no    = 1000
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }
  egress {
    protocol   = "-1"
    rule_no    = 1000
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }
  tags = {
    Name =  format("%s-general", var.bat)
  }
}

################### instances ####################
# Create EC2 linux instance web_server_1
resource "aws_instance" "bat_public_server1" {
  ami                         = var.instance_ami_a41_virginia
  instance_type               = var.instance_type_t2_micro_virginia
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = "10.1.1.100"
  subnet_id                   = aws_subnet.bat_public_subnet.id
  vpc_security_group_ids      = [aws_security_group.bat_sg.id]
  iam_instance_profile = aws_iam_instance_profile.ec2_s3_access_profile.name
  user_data = file(var.update-server)
  tags = {
    Name =  format("%s-pub01", var.bat)
  }
}
# Create EC2 linux instance nat_server_1
resource "aws_instance" "bat_nat_server1" {
  ami                         = var.instance_ami_a41_virginia
  instance_type               = var.instance_type_t2_micro_virginia
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = "10.1.2.100"
  subnet_id                   = aws_subnet.bat_nat_subnet.id
  vpc_security_group_ids      = [aws_security_group.bat_sg.id]
  iam_instance_profile = aws_iam_instance_profile.ec2_s3_access_profile.name
  user_data = file(var.update-server)
  tags = {
    Name =  format("%s-nat01", var.bat)
  }
}
# Create EC2 linux instance private_server_1
resource "aws_instance" "bat_private_server1" {
  ami                         = var.instance_ami_a41_virginia
  instance_type               = var.instance_type_t2_micro_virginia
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = "10.1.3.100"
  subnet_id                   = aws_subnet.bat_private_subnet.id
  vpc_security_group_ids      = [aws_security_group.bat_sg.id]
  iam_instance_profile = aws_iam_instance_profile.ec2_s3_access_profile.name
  user_data = file(var.update-server)
  tags = {
    Name =  format("%s-private01", var.bat)
  }
}

################### VPC endpoints ####################
# interface
resource "aws_vpc_endpoint" "ec2" {
  vpc_id            = aws_vpc.bat.id
  service_name      = "com.amazonaws.us-east-1.ec2"
  vpc_endpoint_type = "Interface"
  subnet_ids         = [aws_subnet.bat_private_subnet.id]
  security_group_ids = [aws_security_group.bat_sg.id,]
  private_dns_enabled = true
}
# gateway
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.bat.id
  service_name = "com.amazonaws.us-east-1.s3"
  route_table_ids = [
    aws_route_table.bat_rtb_private.id
  ]
}

################### IAM role for ec2 instances ####################
# Create Role
resource "aws_iam_role" "ec2_s3_access" {
  name = "ec2_s3_access"
  assume_role_policy = <<-EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": "sts:AssumeRole",
        "Principal": {
          "Service": "ec2.amazonaws.com"
        },
        "Effect": "Allow",
        "Sid": ""
      }
    ]
  }
  EOF
  tags = {
    Name = format("ec2_s3_access")
  }
}
# Create role policy inline
resource "aws_iam_role_policy" "ec2_s3_access_policy" {
  name = "ec2_s3_access_policy"
  role = aws_iam_role.ec2_s3_access.id
  policy = <<-EOF
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": [
          "s3:*"
        ],
        "Effect": "Allow",
        "Resource": "*"
      },
      {
        "Action": [
          "ec2:*"
        ],
        "Effect": "Allow",
        "Resource": "*"
      }
    ]
  }
  EOF
}
resource "aws_iam_instance_profile" "ec2_s3_access_profile" {
  name = "ec2_s3_access_profile"
  role = aws_iam_role.ec2_s3_access.name
}
