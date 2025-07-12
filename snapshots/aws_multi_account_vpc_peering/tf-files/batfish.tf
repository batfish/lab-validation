
##################################### VPC bat ###################################
#################### common ####################
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
data "aws_caller_identity" "requester" {}
output "account_id_requester" {
  value = data.aws_caller_identity.requester.account_id
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
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.bat, var.bat_public_subnet)
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
#################### route tables ####################
# Define route table  - igw
resource "aws_route_table" "bat_rtb_igw" {
  vpc_id = aws_vpc.bat.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.bat_igw.id
  }
  route {
    cidr_block = "10.2.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-bat-fish-r.id
  }
  tags = {
    Name = format("%s-igw", var.bat)
  }
}
# associate igw route table to the public subnet
resource "aws_route_table_association" "bat_rtb_asctn_igw_public" {
  route_table_id = aws_route_table.bat_rtb_igw.id
  subnet_id      = aws_subnet.bat_public_subnet.id
}
############# security-group #############
# Define security-group
resource "aws_security_group" "bat_sg" {
  name = "bat_sg"
  vpc_id = aws_vpc.bat.id
  # SSH access is controlled at NACL
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
      description = "ICMP Access"
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
    Name =  format("%s-general", var.bat)
  }
}
############# NACL #############
resource "aws_network_acl" "bat_nacl" {
  vpc_id = aws_vpc.bat.id
  subnet_ids = [
    aws_subnet.bat_public_subnet.id
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
resource "aws_instance" "bat_server1" {
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key.key_name
  subnet_id                   = aws_subnet.bat_public_subnet.id
  private_ip                  = "10.1.1.100"
  vpc_security_group_ids      = [aws_security_group.bat_sg.id]
  user_data = file(var.update-server)
  tags = {
    Name =  format("%s-web01", var.bat)
  }
}


##################################### VPC fish ###################################
#################### common ####################
# change profile as necessary. Generally profile is "default"
variable "profile_2" {
  description = "account profile"
  default     = "Sandbox2Admin"
}
data "aws_caller_identity" "accepter" {
    provider = aws.accepter
}
output "account_id_accepter" {
  value = data.aws_caller_identity.accepter.account_id
}
#################### fish ####################
# `fish` is the vpc keyword being used for tagging in all resources belongs to this vpc.
# replace `fish` with your prefered name.

variable "fish" {
  description = "VPC Name"
  default     = "fish"
}
variable "fish_cidr" {
  description = "CIDR block for the VPC"
  default     = "10.2.0.0/16"
}
variable "fish_public_subnet" {
  description = "public subnet"
  default     = "10.2.1.0/24"
}

#################### Provider Config ####################
provider "aws" {
  alias = "accepter"
  profile = var.profile_2
  region  = var.vpc_region_ohio
}
# Use existing ssh key pair
resource "aws_key_pair" "ec2key_2" {
  provider = aws.accepter
  key_name = "publicKey"
  public_key = file(var.public_key_path)
}
#################### vpc ####################
# Define VPC
resource "aws_vpc" "fish" {
  provider = aws.accepter
  cidr_block = var.fish_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = var.fish
  }
}

############# Subnets #############
# Define public subnet
resource "aws_subnet" "fish_public_subnet" {
  provider = aws.accepter
  vpc_id     = aws_vpc.fish.id
  cidr_block = var.fish_public_subnet
  map_public_ip_on_launch = "true"
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.fish, var.fish_public_subnet)
  }
}

############# gateways #############
# Define internet gateway
resource "aws_internet_gateway" "fish_igw" {
  provider = aws.accepter
  vpc_id = aws_vpc.fish.id
  tags = {
    Name = var.fish
  }
}
#################### route tables ####################
# Define route table  - igw
resource "aws_route_table" "fish_rtb_igw" {
  provider = aws.accepter
  vpc_id = aws_vpc.fish.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.fish_igw.id
  }
  route {
    cidr_block = "10.1.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-bat-fish-r.id
  }
  tags = {
    Name = format("%s-igw", var.fish)
  }
}
# associate igw route table to the jump subnet
resource "aws_route_table_association" "fish-rtb-asctn-igw-public" {
  provider = aws.accepter
  route_table_id = aws_route_table.fish_rtb_igw.id
  subnet_id      = aws_subnet.fish_public_subnet.id
}
############# security-group #############
# Define security-group
resource "aws_security_group" "fish_sg" {
  provider = aws.accepter
  name = "fish_sg"
  vpc_id = aws_vpc.fish.id
  # SSH access is controlled at NACL
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
      description = "ICMP Access"
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
    Name =  format("%s-general", var.fish)
  }
}
############# NACL #############
resource "aws_network_acl" "fish_nacl" {
  provider = aws.accepter
  vpc_id = aws_vpc.fish.id
  subnet_ids = [
    aws_subnet.fish_public_subnet.id
  ]
  ingress {
    protocol   = "tcp"
    rule_no    = 10
    action     = "allow"
    cidr_block = "10.1.1.100/32"
    from_port  = 22
    to_port    = 22
  }
  ingress {
    protocol   = "tcp"
    rule_no    = 20
    action     = "deny"
    cidr_block = "0.0.0.0/0"
    from_port  = 22
    to_port    = 22
  }
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
    Name =  format("%s-general", var.fish)
  }
}

################### instances ####################
# Create EC2 linux instance web_server_1
resource "aws_instance" "fish_server1" {
  provider = aws.accepter
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key_2.key_name
  subnet_id                   = aws_subnet.fish_public_subnet.id
  vpc_security_group_ids      = [aws_security_group.fish_sg.id]
  user_data = file(var.update-server)
  tags = {
    Name =  format("%s-web01", var.fish)
  }
}

#################### VPC Peering ####################
# Requester
resource "aws_vpc_peering_connection" "pcx-bat-fish-r" {
  vpc_id        = aws_vpc.bat.id
  peer_vpc_id   = aws_vpc.fish.id
  peer_owner_id = data.aws_caller_identity.accepter.account_id
  auto_accept   = false
  tags = {
    Name = "pcx-bat-fish-r"
  }
}
# Accepter
resource "aws_vpc_peering_connection_accepter" "pcx-bat-fish-a" {
  provider = aws.accepter
  vpc_peering_connection_id = aws_vpc_peering_connection.pcx-bat-fish-r.id
  auto_accept               = true
  tags = {
    Name = "pcx-bat-fish-a"
  }
}
