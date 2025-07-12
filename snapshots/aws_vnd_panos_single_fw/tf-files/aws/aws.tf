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
variable "instance_ami_a41" {
  description = "AMI for aws EC2 instance"
  default     = "ami-0fc61db8544a617ed"
}
variable "instance_type_t2_micro" {
  description = "type for aws EC2 instance"
  default     = "t2.micro"
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
variable "instance_ami_pa_fw" {
  description = "AMI for PA FW"
  default     = "ami-0619acd2e9d26ea1e"
}
variable "instance_type_pa_fw_m5_xlarge" {
  description = "type for PA FW"
  default     = "m5.xlarge"
}

##################################### VPC vnd_panos ###################################
#################### VPC vnd_panos vars ####################
# `vnd_panos` is the vpc keyword being used for tagging in all resources belongs to this vpc.
# replace `vnd_panos` with your prefered name.

variable "vnd_panos" {
  description = "VPC Name"
  default     = "vnd_panos"
}
variable "vnd_panos_cidr" {
  description = "CIDR block for the VPC"
  default     = "10.1.0.0/16"
}
variable "vnd_panos_public_subnet" {
  description = "public subnet"
  default     = "10.1.1.0/24"
}
variable "vnd_panos_private_subnet" {
  description = "private subnet"
  default     = "10.1.101.0/24"
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
resource "aws_vpc" "vnd_panos" {
  cidr_block = var.vnd_panos_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = var.vnd_panos
  }
}

############# Subnets #############
# Define public subnet
resource "aws_subnet" "vnd_panos_public_subnet" {
  vpc_id     = aws_vpc.vnd_panos.id
  cidr_block = var.vnd_panos_public_subnet
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_public_subnet", var.vnd_panos)
  }
}
# Define private subnet
resource "aws_subnet" "vnd_panos_private_subnet" {
  vpc_id     = aws_vpc.vnd_panos.id
  cidr_block = var.vnd_panos_private_subnet
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_private_subnet", var.vnd_panos)
  }
}

#################### igw-ngw ####################
# Define igw
resource "aws_internet_gateway" "vnd_panos_igw" {
  vpc_id     = aws_vpc.vnd_panos.id
  tags = {
    Name = format("vnd_panos_igw")
  }
}

#################### route tables ####################
# Define route table - public
resource "aws_route_table" "vnd_panos_rtb_public" {
  vpc_id = aws_vpc.vnd_panos.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.vnd_panos_igw.id
  }
  tags = {
    Name = format("%s_rtb_public", var.vnd_panos)
  }
}
# associate route table to vnd_panos_public_subnet
resource "aws_route_table_association" "vnd_panos_rtb_asctn_vnd_panos_public_subnet" {
  route_table_id = aws_route_table.vnd_panos_rtb_public.id
  subnet_id      = aws_subnet.vnd_panos_public_subnet.id
}
# Define route table  - private
resource "aws_route_table" "vnd_panos_rtb_private" {
  vpc_id = aws_vpc.vnd_panos.id
  tags = {
    Name = format("%s_rtb_private", var.vnd_panos)
  }
}
# associate route table to vnd_panos_vnd_panos_private_subnet
resource "aws_route_table_association" "vnd_panos_rtb_asctn_vnd_panos_vnd_panos_private_subnet" {
  route_table_id = aws_route_table.vnd_panos_rtb_private.id
  subnet_id      = aws_subnet.vnd_panos_private_subnet.id
}
resource "aws_route" "private_default_to_fw" {
  route_table_id            = aws_route_table.vnd_panos_rtb_private.id
  destination_cidr_block    = "0.0.0.0/0"
  network_interface_id      = aws_network_interface.vnd_panos_fw_ni_trusted.id
  depends_on                = [aws_route_table.vnd_panos_rtb_private]
}
############# security-group #############
# Define security-group
resource "aws_security_group" "vnd_panos_sg_general" {
  name = "vnd_panos_sg_general"
  vpc_id = aws_vpc.vnd_panos.id
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
    Name =  format("%s_general", var.vnd_panos)
  }
}
resource "aws_security_group" "vnd_panos_sg_mgmt" {
  name = "vnd_panos_sg_mgmt"
  vpc_id = aws_vpc.vnd_panos.id
  ingress {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "SSH Access"
  }
  ingress {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "HTTPS Access"
  }
  ingress {
      from_port   = 8
      to_port     = 0
      protocol    = "icmp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "ICMP Echo Request Access"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all"
  }
  tags = {
    Name =  format("%s_mgmt", var.vnd_panos)
  }
}
resource "aws_security_group" "vnd_panos_sg_untrusted" {
  name = "vnd_panos_sg_untrusted"
  vpc_id = aws_vpc.vnd_panos.id
  ingress {
      from_port   = 21
      to_port     = 21
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "SSH Access"
  }
  ingress {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "SSH Access"
  }
  ingress {
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "SSH Access"
  }
  ingress {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "HTTPS Access"
  }
  ingress {
    from_port   = 8
    to_port     = 0
    protocol    = "icmp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "ICMP Access"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all"
  }
  tags = {
    Name =  format("%s_untrusted", var.vnd_panos)
  }
}
resource "aws_security_group" "vnd_panos_sg_trusted" {
  name = "vnd_panos_sg_trusted"
  vpc_id = aws_vpc.vnd_panos.id
  ingress {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = ["10.1.1.100/32"]
      description = "SSH Access only from jump"
  }
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
    Name =  format("%s_trusted", var.vnd_panos)
  }
}
############# NACL #############
resource "aws_network_acl" "vnd_panos_nacl_general" {
  vpc_id = aws_vpc.vnd_panos.id
  subnet_ids = [
    aws_subnet.vnd_panos_public_subnet.id,
    aws_subnet.vnd_panos_private_subnet.id
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
    Name =  format("%s_general", var.vnd_panos)
  }
}
################## instances ####################
# Create EC2 linux instance - vnd_panos jump servers
resource "aws_instance" "vnd_panos_jump" {
  count = 1
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = "10.1.1.100"
  associate_public_ip_address = "true"
  subnet_id                   = aws_subnet.vnd_panos_public_subnet.id
  vpc_security_group_ids      = [aws_security_group.vnd_panos_sg_general.id]
  user_data = file(var.update-server)
  tags = {
    Name =  format("vnd_panos_jump0%s",count.index+1)
  }
}
# Create EC2 linux instance - vnd_panos web servers
resource "aws_instance" "vnd_panos_web" {
  count = 1
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = "10.1.101.100"
  subnet_id                   = aws_subnet.vnd_panos_private_subnet.id
  vpc_security_group_ids      = [aws_security_group.vnd_panos_sg_trusted.id]
  user_data                   = file(var.create-web-server)
  tags = {
    Name =  format("vnd_panos_web0%s",count.index+1)
  }
}

################## PA FW in AWS ####################
# Network Interfaces
resource "aws_network_interface" "vnd_panos_fw_ni_mgmt" {
  subnet_id       = aws_subnet.vnd_panos_public_subnet.id
  security_groups = [aws_security_group.vnd_panos_sg_mgmt.id]
  source_dest_check = false
  private_ips = ["10.1.1.101"]
  tags = {
    Name =  format("vnd_panos_fw_ni_mgmt")
  }
}
resource "aws_network_interface" "vnd_panos_fw_ni_untrusted" {
  subnet_id       = aws_subnet.vnd_panos_public_subnet.id
  security_groups = [aws_security_group.vnd_panos_sg_untrusted.id]
  source_dest_check = false
  private_ips = ["10.1.1.10"]
  tags = {
    Name =  format("vnd_panos_fw_ni_untrusted")
  }
}
resource "aws_network_interface" "vnd_panos_fw_ni_trusted" {
  subnet_id       = aws_subnet.vnd_panos_private_subnet.id
  security_groups = [aws_security_group.vnd_panos_sg_trusted.id]
  source_dest_check = false
  private_ips = ["10.1.101.10"]
  tags = {
    Name =  format("vnd_panos_fw_ni_trusted")
  }
}

# EIP & associattion
resource "aws_eip" "vnd_panos_fw_ni_mgmt_eip" {
  vpc   = true
  depends_on = [aws_vpc.vnd_panos, aws_internet_gateway.vnd_panos_igw]
}
resource "aws_eip" "vnd_panos_fw_ni_untrusted_eip" {
  vpc   = true
  depends_on = [aws_vpc.vnd_panos, aws_internet_gateway.vnd_panos_igw]
}
resource "aws_eip_association" "vnd_panos_fw_ni_mgmt_eip_asctn" {
  network_interface_id   = aws_network_interface.vnd_panos_fw_ni_mgmt.id
  allocation_id = aws_eip.vnd_panos_fw_ni_mgmt_eip.id
}
resource "aws_eip_association" "vnd_panos_fw_ni_untrusted_eip_asctn" {
  network_interface_id   = aws_network_interface.vnd_panos_fw_ni_untrusted.id
  allocation_id = aws_eip.vnd_panos_fw_ni_untrusted_eip.id
}

# Create PA_FW instance
resource "aws_instance" "vnd_panos_fw01" {
  ami                         = var.instance_ami_pa_fw
  instance_type               = var.instance_type_pa_fw_m5_xlarge
  key_name                    = aws_key_pair.ec2key.key_name
  disable_api_termination = false
  instance_initiated_shutdown_behavior = "stop"
  monitoring = false
  ebs_optimized = true
  network_interface {
    device_index = 0
    network_interface_id   = aws_network_interface.vnd_panos_fw_ni_mgmt.id
  }
  network_interface {
    device_index = 1
    network_interface_id = aws_network_interface.vnd_panos_fw_ni_untrusted.id
  }
  network_interface {
    device_index = 2
    network_interface_id = aws_network_interface.vnd_panos_fw_ni_trusted.id
  }
  tags = {
    Name =  format("vnd_panos_fw01")
  }
}

output "mgmt_ip_pub" {
  value = aws_eip.vnd_panos_fw_ni_mgmt_eip.public_ip
}
