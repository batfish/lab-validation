#################### common vars ####################
variable "vpc_region_ohio" {
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
variable "ec2-instance-type" {
  description = "type for aws EC2 instance"
  default     = "t2.micro"
}
variable "ec2-instance-ami-west" {
  description = "AMI for aws EC2 instance"
  default     = "ami-09a7fe78668f1e2c0"
}
variable "ec2-instance-ami-east" {
  description = "AMI for aws EC2 instance"
  default     = "ami-0a887e401f7654935"
}
variable "update-server" {
  description = "update server and install nmap and nc"
  default = "update-server.sh"
}
variable "create-web-server" {
  description = "create web server, update server and install nmap and nc"
  default = "create-web-server.sh"
}
data "aws_caller_identity" "requester" {}
output "account_id_requester" {
  value = data.aws_caller_identity.requester.account_id
}


##################################### VPC multi_iface ###################################
#################### VPC multi_iface vars ####################
# `multi_iface` is the vpc keyword being used for tagging in all resources belongs to this vpc.
# replace `multi_iface` with your prefered name.

variable "multi_iface" {
  description = "VPC Name"
  default     = "multi_iface"
}
variable "multi_iface_cidr" {
  description = "CIDR block for the VPC"
  default     = "10.1.0.0/16"
}
variable "multi_iface_jump_subnet" {
  description = "public subnet"
  default     = "10.1.1.0/24"
}
variable "multi_iface_public_subnet" {
  description = "public subnet"
  default     = "10.1.2.0/24"
}
variable "multi_iface_private_subnet" {
  description = "private subnet"
  default     = "10.1.102.0/24"
}
data "aws_availability_zones" "az" {
  state = "available"
}

#################### Provider Config ####################
provider "aws" {
  profile = var.profile
  region  = var.vpc_region_ohio
}
# Use existing ssh key pair
resource "aws_key_pair" "ec2key" {
  key_name = "publicKey"
  public_key = file(var.public_key_path)
}

#################### vpc ####################
# Define VPC
resource "aws_vpc" "multi_iface" {
  cidr_block = var.multi_iface_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = var.multi_iface
  }
}

############# Subnets #############
# Define jump subnet
resource "aws_subnet" "multi_iface_jump_subnet" {
  vpc_id     = aws_vpc.multi_iface.id
  cidr_block = var.multi_iface_jump_subnet
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_jump_subnet", var.multi_iface)
  }
}
# Define public subnet
resource "aws_subnet" "multi_iface_public_subnet" {
  vpc_id     = aws_vpc.multi_iface.id
  cidr_block = var.multi_iface_public_subnet
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_public_subnet", var.multi_iface)
  }
}
# Define private subnet
resource "aws_subnet" "multi_iface_private_subnet" {
  vpc_id     = aws_vpc.multi_iface.id
  cidr_block = var.multi_iface_private_subnet
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_private_subnet", var.multi_iface)
  }
}

#################### igw-ngw ####################
# Define igw
resource "aws_internet_gateway" "multi_iface_igw" {
  vpc_id     = aws_vpc.multi_iface.id
  tags = {
    Name = format("multi_iface_igw")
  }
}

#################### route tables ####################
# Define route table - public
resource "aws_route_table" "multi_iface_rtb_public" {
  vpc_id = aws_vpc.multi_iface.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.multi_iface_igw.id
  }
  tags = {
    Name = format("%s_rtb_public", var.multi_iface)
  }
}
# associate route table to multi_iface_jump_subnet
resource "aws_route_table_association" "multi_iface_rtb_asctn_multi_iface_jump_subnet" {
  route_table_id = aws_route_table.multi_iface_rtb_public.id
  subnet_id      = aws_subnet.multi_iface_jump_subnet.id
}
# associate route table to multi_iface_public_subnet
resource "aws_route_table_association" "multi_iface_rtb_asctn_multi_iface_public_subnet" {
  route_table_id = aws_route_table.multi_iface_rtb_public.id
  subnet_id      = aws_subnet.multi_iface_public_subnet.id
}
# Define route table  - private
resource "aws_route_table" "multi_iface_rtb_private" {
  vpc_id = aws_vpc.multi_iface.id
  tags = {
    Name = format("%s_rtb_private", var.multi_iface)
  }
}
# associate route table to multi_iface_multi_iface_private_subnet
resource "aws_route_table_association" "multi_iface_rtb_asctn_multi_iface_multi_iface_private_subnet" {
  route_table_id = aws_route_table.multi_iface_rtb_private.id
  subnet_id      = aws_subnet.multi_iface_private_subnet.id
}

############# security-group #############
# Define security-group
resource "aws_security_group" "multi_iface_sg_general" {
  name = "multi_iface_sg_general"
  vpc_id = aws_vpc.multi_iface.id
  ingress {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "SSH Access"
  }
  ingress {
      from_port   = 8
      to_port     = 0
      protocol    = "icmp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "ICMP Echo Request Access"
  }
  ingress {
      from_port   = 33434
      to_port     = 33534
      protocol    = "udp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "Traceroute Access"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all"
  }
  tags = {
    Name =  format("%s_general", var.multi_iface)
  }
}
resource "aws_security_group" "multi_iface_sg_internet_allowed" {
  name = "multi_iface_sg_internet_allowed"
  vpc_id = aws_vpc.multi_iface.id
  ingress {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "SSH Access"
  }
  ingress {
      from_port   = 8
      to_port     = 0
      protocol    = "icmp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "ICMP Echo Request Access"
  }
  ingress {
      from_port   = 33434
      to_port     = 33534
      protocol    = "udp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "Traceroute Access"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all"
  }
  tags = {
    Name =  format("%s_internet_allowed", var.multi_iface)
  }
}
resource "aws_security_group" "multi_iface_sg_internet_blocked" {
  name = "multi_iface_sg_internet_blocked"
  vpc_id = aws_vpc.multi_iface.id
  ingress {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [var.multi_iface_jump_subnet]
      description = "SSH Access"
  }
  ingress {
      from_port   = 8
      to_port     = 0
      protocol    = "icmp"
      cidr_blocks = [var.multi_iface_jump_subnet]
      description = "ICMP Echo Request Access"
  }
  ingress {
      from_port   = 33434
      to_port     = 33534
      protocol    = "udp"
      cidr_blocks = [var.multi_iface_jump_subnet]
      description = "Traceroute Access"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all"
  }
  tags = {
    Name =  format("%s_internet_blocked", var.multi_iface)
  }
}
resource "aws_security_group" "multi_iface_sg_jump_test_allowed" {
  name = "multi_iface_sg_jump_test_allowed"
  vpc_id = aws_vpc.multi_iface.id
  ingress {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [var.multi_iface_jump_subnet]
      description = "SSH Access"
  }
  ingress {
      from_port   = 8
      to_port     = 0
      protocol    = "icmp"
      cidr_blocks = [var.multi_iface_jump_subnet]
      description = "ICMP Echo Request Access"
  }
  ingress {
      from_port   = 33434
      to_port     = 33534
      protocol    = "udp"
      cidr_blocks = [var.multi_iface_jump_subnet]
      description = "Traceroute Access"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all"
  }
  tags = {
    Name =  format("%s_jump_test_allowed", var.multi_iface)
  }
}
resource "aws_security_group" "multi_iface_sg_jump_test_blocked" {
  name = "multi_iface_sg_jump_test_blocked"
  vpc_id = aws_vpc.multi_iface.id
  ingress {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = ["10.1.1.100/32"]
      description = "SSH Access"
  }
  ingress {
      from_port   = 8
      to_port     = 0
      protocol    = "icmp"
      cidr_blocks = ["10.1.1.100/32"]
      description = "ICMP Echo Request Access"
  }
  ingress {
      from_port   = 33434
      to_port     = 33534
      protocol    = "udp"
      cidr_blocks = ["10.1.1.100/32"]
      description = "Traceroute Access"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all"
  }
  tags = {
    Name =  format("%s_jump_test_blocked", var.multi_iface)
  }
}

############# NACL #############
resource "aws_network_acl" "multi_iface_nacl_general" {
  vpc_id = aws_vpc.multi_iface.id
  subnet_ids = [
    aws_subnet.multi_iface_jump_subnet.id,
    aws_subnet.multi_iface_public_subnet.id,
    aws_subnet.multi_iface_private_subnet.id
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
    Name =  format("%s_general", var.multi_iface)
  }
}
################## instances ####################
# Create EC2 linux instance - multi_iface jump instances
resource "aws_instance" "multi_iface_jump" {
  count = 1
  ami                         = var.ec2-instance-ami-east
  instance_type               = var.ec2-instance-type
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = "10.1.1.100"
  associate_public_ip_address = "true"
  subnet_id                   = aws_subnet.multi_iface_jump_subnet.id
  vpc_security_group_ids      = [aws_security_group.multi_iface_sg_general.id]
  user_data = file(var.update-server)
  tags = {
    Name =  format("multi_iface_jump0%s",count.index+1)
  }
}
resource "aws_instance" "multi_iface_jump_test" {
  count = 1
  ami                         = var.ec2-instance-ami-east
  instance_type               = var.ec2-instance-type
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = "10.1.1.101"
  associate_public_ip_address = "true"
  subnet_id                   = aws_subnet.multi_iface_jump_subnet.id
  vpc_security_group_ids      = [aws_security_group.multi_iface_sg_general.id]
  user_data = file(var.update-server)
  tags = {
    Name =  format("multi_iface_jump_test0%s",count.index+1)
  }
}

###### Create EC2 linux instance - multi_iface public instances ######
# Network Interfaces
resource "aws_network_interface" "multi_iface_pub_ni_1" {
  subnet_id       = aws_subnet.multi_iface_public_subnet.id
  security_groups = [aws_security_group.multi_iface_sg_internet_allowed.id]
  private_ips = ["10.1.2.101"]
  tags = {
    Name =  format("multi_iface_pub_ni_1")
  }
}
resource "aws_network_interface" "multi_iface_pub_ni_2" {
  subnet_id       = aws_subnet.multi_iface_public_subnet.id
  security_groups = [aws_security_group.multi_iface_sg_internet_blocked.id]
  private_ips = ["10.1.2.102"]
  tags = {
    Name =  format("multi_iface_pub_ni_2")
  }
}
# EIP & associattion
resource "aws_eip" "multi_iface_pub_ni_1_eip" {
  vpc   = true
  depends_on = [aws_vpc.multi_iface, aws_internet_gateway.multi_iface_igw]
}
resource "aws_eip" "multi_iface_pub_ni_2_eip" {
  vpc   = true
  depends_on = [aws_vpc.multi_iface, aws_internet_gateway.multi_iface_igw]
}
resource "aws_eip_association" "multi_iface_pub_ni_1_eip_asctn" {
  network_interface_id   = aws_network_interface.multi_iface_pub_ni_1.id
  allocation_id = aws_eip.multi_iface_pub_ni_1_eip.id
}
resource "aws_eip_association" "multi_iface_pub_ni_2_eip_asctn" {
  network_interface_id   = aws_network_interface.multi_iface_pub_ni_2.id
  allocation_id = aws_eip.multi_iface_pub_ni_2_eip.id
}
# instnace
resource "aws_instance" "multi_iface_public" {
  count = 1
  ami                         = var.ec2-instance-ami-east
  instance_type               = var.ec2-instance-type
  key_name                    = aws_key_pair.ec2key.key_name
  user_data = file(var.create-web-server)
  network_interface {
    device_index = 0
    network_interface_id = aws_network_interface.multi_iface_pub_ni_1.id
  }
  network_interface {
    device_index = 1
    network_interface_id = aws_network_interface.multi_iface_pub_ni_2.id
  }
  tags = {
    Name =  format("multi_iface_public0%s",count.index+1)
  }
}

###### Create EC2 linux instance - multi_iface private instances ######
# Network Interfaces
resource "aws_network_interface" "multi_iface_pri_ni_1" {
  subnet_id       = aws_subnet.multi_iface_private_subnet.id
  security_groups = [aws_security_group.multi_iface_sg_jump_test_allowed.id]
  private_ips = ["10.1.102.101"]
  tags = {
    Name =  format("multi_iface_pri_ni_1")
  }
}
resource "aws_network_interface" "multi_iface_pri_ni_2" {
  subnet_id       = aws_subnet.multi_iface_private_subnet.id
  security_groups = [aws_security_group.multi_iface_sg_jump_test_blocked.id]
  private_ips = ["10.1.102.102"]
  tags = {
    Name =  format("multi_iface_pri_ni_2")
  }
}
# instnace
resource "aws_instance" "multi_iface_private" {
  count = 1
  ami                         = var.ec2-instance-ami-east
  instance_type               = var.ec2-instance-type
  key_name                    = aws_key_pair.ec2key.key_name
  user_data = file(var.create-web-server)
  network_interface {
    device_index = 0
    network_interface_id = aws_network_interface.multi_iface_pri_ni_1.id
  }
  network_interface {
    device_index = 1
    network_interface_id = aws_network_interface.multi_iface_pri_ni_2.id
  }
  tags = {
    Name =  format("multi_iface_private0%s",count.index+1)
  }
}
