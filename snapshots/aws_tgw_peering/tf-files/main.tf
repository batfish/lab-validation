
##################################### VPC account ###################################
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
  default     = "ami-0fc61db8544a617ed"
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

#################### account ####################
# `account` is the vpc keyword being used for tagging in all resources belongs to this vpc.
# replace `account` with your prefered name.

variable "account" {
  description = "VPC Name"
  default     = "account"
}
variable "account_cidr" {
  description = "CIDR block for the VPC"
  default     = "10.1.0.0/16"
}
variable "account_public_subnet" {
  description = "public subnet"
  default     = "10.1.1.0/24"
}
variable "account_tgw_subnet" {
  description = "tgw subnet"
  default     = "10.1.250.0/24"
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
resource "aws_vpc" "account" {
  cidr_block = var.account_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = var.account
  }
}

############# Subnets #############
# Define public subnet
resource "aws_subnet" "account_public_subnet" {
  vpc_id     = aws_vpc.account.id
  cidr_block = var.account_public_subnet
  map_public_ip_on_launch = "true"
  availability_zone = data.aws_availability_zones.az_virginia.names[0]
  tags = {
    Name = format("%s_%s", var.account, var.account_public_subnet)
  }
}
# Define tgw subnet
resource "aws_subnet" "account_tgw_subnet" {
  vpc_id     = aws_vpc.account.id
  cidr_block = var.account_tgw_subnet
  availability_zone = data.aws_availability_zones.az_virginia.names[0]
  tags = {
    Name = format("%s_%s", var.account, var.account_tgw_subnet)
  }
}
############# gateways #############
# Define internet gateway
resource "aws_internet_gateway" "account_igw" {
  vpc_id = aws_vpc.account.id
  tags = {
    Name = var.account
  }
}
#################### route tables ####################
# Define route table  - igw
resource "aws_route_table" "account_rtb_igw" {
  vpc_id = aws_vpc.account.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.account_igw.id
  }
  route {
    cidr_block = "10.2.0.0/16"
    transit_gateway_id = aws_ec2_transit_gateway.tgw-virginia.id
  }
  route {
    cidr_block = "10.3.0.0/16"
    transit_gateway_id = aws_ec2_transit_gateway.tgw-virginia.id
  }
  tags = {
    Name = format("%s-igw", var.account)
  }
}
# associate igw route table to the public subnet
resource "aws_route_table_association" "account_rtb_asctn_igw_public" {
  route_table_id = aws_route_table.account_rtb_igw.id
  subnet_id      = aws_subnet.account_public_subnet.id
}
# associate igw route table to the tgw subnet
resource "aws_route_table_association" "account_rtb_asctn_igw_tgw" {
  route_table_id = aws_route_table.account_rtb_igw.id
  subnet_id      = aws_subnet.account_tgw_subnet.id
}
############# security-group #############
# Define security-group
resource "aws_security_group" "account_sg" {
  name = "account_sg"
  vpc_id = aws_vpc.account.id
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
    Name =  format("%s-general", var.account)
  }
}
############# NACL #############
resource "aws_network_acl" "account_nacl" {
  vpc_id = aws_vpc.account.id
  subnet_ids = [
    aws_subnet.account_public_subnet.id
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
    Name =  format("%s-general", var.account)
  }
}
resource "aws_network_acl" "account_tgw_nacl" {
  vpc_id = aws_vpc.account.id
  subnet_ids = [
    aws_subnet.account_tgw_subnet.id
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
    Name =  format("%s-tgw", var.account)
  }
}

################### instances ####################
# Create EC2 linux instance web_server_1
resource "aws_instance" "account_server1" {
  ami                         = var.instance_ami_a41_virginia
  instance_type               = var.instance_type_t2_micro_virginia
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = "10.1.1.100"
  subnet_id                   = aws_subnet.account_public_subnet.id
  vpc_security_group_ids      = [aws_security_group.account_sg.id]
  user_data = file(var.update-server)
  tags = {
    Name =  format("%s-web01", var.account)
  }
}



##################################### VPC different ###################################
#################### common ####################
# change profile as necessary. Generally profile is "default"
variable "vpc_region_ohio" {
  description = "VPC Region"
  default     = "us-east-2"
}
variable "profile_2" {
  description = "account profile"
  default     = "Sandbox2Admin"
}
data "aws_caller_identity" "accepter_different" {
    provider = aws.ohio
}
output "account_id_accepter_different" {
  value = data.aws_caller_identity.accepter_different.account_id
}
variable "instance_ami_a41_ohio" {
  description = "AMI for aws EC2 instance"
  default     = "ami-0f7919c33c90f5b58"
}
variable "instance_type_t2_micro_ohio" {
  description = "type for aws EC2 instance"
  default     = "t2.micro"
}
#################### different ####################
# `different` is the vpc keyword being used for tagging in all resources belongs to this vpc.
# replace `different` with your prefered name.

variable "different" {
  description = "VPC Name"
  default     = "different"
}
variable "different_cidr" {
  description = "CIDR block for the VPC"
  default     = "10.2.0.0/16"
}
variable "different_public_subnet" {
  description = "public subnet"
  default     = "10.2.1.0/24"
}
variable "different_tgw_subnet" {
  description = "tgw subnet"
  default     = "10.2.250.0/24"
}

#################### Provider Config ####################
provider "aws" {
  alias = "ohio"
  profile = var.profile_2
  region  = var.vpc_region_ohio
}
# Use existing ssh key pair
resource "aws_key_pair" "ec2key_2" {
  provider = aws.ohio
  key_name = "publicKey"
  public_key = file(var.public_key_path)
}
data "aws_availability_zones" "az_ohio" {
  provider = aws.ohio
  state = "available"
}
#################### vpc ####################
# Define VPC
resource "aws_vpc" "different" {
  provider = aws.ohio
  cidr_block = var.different_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = var.different
  }
}

############# Subnets #############
# Define public subnet
resource "aws_subnet" "different_public_subnet" {
  provider = aws.ohio
  vpc_id     = aws_vpc.different.id
  cidr_block = var.different_public_subnet
  map_public_ip_on_launch = "true"
  availability_zone = data.aws_availability_zones.az_ohio.names[0]
  tags = {
    Name = format("%s_%s", var.different, var.different_public_subnet)
  }
}
# Define tgw subnet
resource "aws_subnet" "different_tgw_subnet" {
  provider = aws.ohio
  vpc_id     = aws_vpc.different.id
  cidr_block = var.different_tgw_subnet
  availability_zone = data.aws_availability_zones.az_ohio.names[0]
  tags = {
    Name = format("%s_%s", var.different, var.different_tgw_subnet)
  }
}

############# gateways #############
# Define internet gateway
resource "aws_internet_gateway" "different_igw" {
  provider = aws.ohio
  vpc_id = aws_vpc.different.id
  tags = {
    Name = var.different
  }
}
#################### route tables ####################
# Define route table  - igw
resource "aws_route_table" "different_rtb_igw" {
  provider = aws.ohio
  vpc_id = aws_vpc.different.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.different_igw.id
  }
  route {
    cidr_block = "10.1.0.0/16"
    transit_gateway_id = aws_ec2_transit_gateway.tgw-ohio.id
  }
  tags = {
    Name = format("%s-igw", var.different)
  }
}
# associate igw route table to the jump subnet
resource "aws_route_table_association" "different-rtb-asctn-igw-public" {
  provider = aws.ohio
  route_table_id = aws_route_table.different_rtb_igw.id
  subnet_id      = aws_subnet.different_public_subnet.id
}
# associate igw route table to the tgw subnet
resource "aws_route_table_association" "different-rtb-asctn-igw-tgw" {
  provider = aws.ohio
  route_table_id = aws_route_table.different_rtb_igw.id
  subnet_id      = aws_subnet.different_tgw_subnet.id
}
############# security-group #############
# Define security-group
resource "aws_security_group" "different_sg" {
  provider = aws.ohio
  name = "different_sg"
  vpc_id = aws_vpc.different.id
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
    Name =  format("%s-general", var.different)
  }
}
############# NACL #############
resource "aws_network_acl" "different_nacl" {
  provider = aws.ohio
  vpc_id = aws_vpc.different.id
  subnet_ids = [
    aws_subnet.different_public_subnet.id
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
    Name =  format("%s-general", var.different)
  }
}
resource "aws_network_acl" "different_tgw_nacl" {
  provider = aws.ohio
  vpc_id = aws_vpc.different.id
  subnet_ids = [
    aws_subnet.different_tgw_subnet.id
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
    Name =  format("%s-tgw", var.different)
  }
}

################### instances ####################
# Create EC2 linux instance web_server_1
resource "aws_instance" "different_server1" {
  provider = aws.ohio
  ami                         = var.instance_ami_a41_ohio
  instance_type               = var.instance_type_t2_micro_ohio
  key_name                    = aws_key_pair.ec2key_2.key_name
  subnet_id                   = aws_subnet.different_public_subnet.id
  private_ip                  = "10.2.1.100"
  vpc_security_group_ids      = [aws_security_group.different_sg.id]
  user_data = file(var.update-server)
  tags = {
    Name =  format("%s-web01", var.different)
  }
}




##################################### VPC same ###################################
#################### common ####################
# change profile as necessary. Generally profile is "default"
variable "vpc_region_california" {
  description = "VPC Region"
  default     = "us-west-1"
}
data "aws_caller_identity" "accepter_same" {
    provider = aws.california
}
output "account_id_accepter_same" {
  value = data.aws_caller_identity.accepter_same.account_id
}
variable "instance_ami_a41_california" {
  description = "AMI for aws EC2 instance"
  default     = "ami-06fcc1f0bc2c8943f"
}
variable "instance_type_t2_micro_california" {
  description = "type for aws EC2 instance"
  default     = "t2.micro"
}
#################### same ####################
# `same` is the vpc keyword being used for tagging in all resources belongs to this vpc.
# replace `same` with your prefered name.

variable "same" {
  description = "VPC Name"
  default     = "same"
}
variable "same_cidr" {
  description = "CIDR block for the VPC"
  default     = "10.3.0.0/16"
}
variable "same_public_subnet" {
  description = "public subnet"
  default     = "10.3.1.0/24"
}
variable "same_tgw_subnet" {
  description = "tgw subnet"
  default     = "10.3.250.0/24"
}

#################### Provider Config ####################
provider "aws" {
  alias = "california"
  profile = var.profile
  region  = var.vpc_region_california
}
# Use existing ssh key pair
resource "aws_key_pair" "ec2key_3" {
  provider = aws.california
  key_name = "publicKey"
  public_key = file(var.public_key_path)
}
data "aws_availability_zones" "az_california" {
  provider = aws.california
  state = "available"
}
#################### vpc ####################
# Define VPC
resource "aws_vpc" "same" {
  provider = aws.california
  cidr_block = var.same_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = var.same
  }
}

############# Subnets #############
# Define public subnet
resource "aws_subnet" "same_public_subnet" {
  provider = aws.california
  vpc_id     = aws_vpc.same.id
  cidr_block = var.same_public_subnet
  map_public_ip_on_launch = "true"
  availability_zone = data.aws_availability_zones.az_california.names[0]
  tags = {
    Name = format("%s_%s", var.same, var.same_public_subnet)
  }
}
# Define tgw subnet
resource "aws_subnet" "same_tgw_subnet" {
  provider = aws.california
  vpc_id     = aws_vpc.same.id
  cidr_block = var.same_tgw_subnet
  availability_zone = data.aws_availability_zones.az_california.names[0]
  tags = {
    Name = format("%s_%s", var.same, var.same_tgw_subnet)
  }
}

############# gateways #############
# Define internet gateway
resource "aws_internet_gateway" "same_igw" {
  provider = aws.california
  vpc_id = aws_vpc.same.id
  tags = {
    Name = var.same
  }
}
#################### route tables ####################
# Define route table  - igw
resource "aws_route_table" "same_rtb_igw" {
  provider = aws.california
  vpc_id = aws_vpc.same.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.same_igw.id
  }
  route {
    cidr_block = "10.1.0.0/16"
    transit_gateway_id = aws_ec2_transit_gateway.tgw-california.id
  }
  tags = {
    Name = format("%s-igw", var.same)
  }
}
# associate igw route table to the jump subnet
resource "aws_route_table_association" "same-rtb-asctn-igw-public" {
  provider = aws.california
  route_table_id = aws_route_table.same_rtb_igw.id
  subnet_id      = aws_subnet.same_public_subnet.id
}
# associate igw route table to the tgw subnet
resource "aws_route_table_association" "same-rtb-asctn-igw-tgw" {
  provider = aws.california
  route_table_id = aws_route_table.same_rtb_igw.id
  subnet_id      = aws_subnet.same_tgw_subnet.id
}
############# security-group #############
# Define security-group
resource "aws_security_group" "same_sg" {
  provider = aws.california
  name = "same_sg"
  vpc_id = aws_vpc.same.id
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
    Name =  format("%s-general", var.same)
  }
}
############# NACL #############
resource "aws_network_acl" "same_nacl" {
  provider = aws.california
  vpc_id = aws_vpc.same.id
  subnet_ids = [
    aws_subnet.same_public_subnet.id
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
    Name =  format("%s-general", var.same)
  }
}
resource "aws_network_acl" "same_tgw_nacl" {
  provider = aws.california
  vpc_id = aws_vpc.same.id
  subnet_ids = [
    aws_subnet.same_tgw_subnet.id
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
    Name =  format("%s-tgw", var.same)
  }
}

################### instances ####################
# Create EC2 linux instance web_server_1
resource "aws_instance" "same_server1" {
  provider = aws.california
  ami                         = var.instance_ami_a41_california
  instance_type               = var.instance_type_t2_micro_california
  key_name                    = aws_key_pair.ec2key_3.key_name
  subnet_id                   = aws_subnet.same_public_subnet.id
  private_ip                  = "10.3.1.100"
  vpc_security_group_ids      = [aws_security_group.same_sg.id]
  user_data = file(var.update-server)
  tags = {
    Name =  format("%s-web01", var.same)
  }
}



#################### TGW ####################
# Create TGW virginia
resource "aws_ec2_transit_gateway" "tgw-virginia" {
  tags = {
        Name = format("tgw-virginia")
    }
}
# Create TGW ohio
resource "aws_ec2_transit_gateway" "tgw-ohio" {
  provider = aws.ohio
  tags = {
        Name = format("tgw-ohio")
    }
}
# Create TGW california
resource "aws_ec2_transit_gateway" "tgw-california" {
  provider = aws.california
  tags = {
        Name = format("tgw-california")
    }
}
# TGW Peering between virginia & ohio
resource "aws_ec2_transit_gateway_peering_attachment" "tgw-peering-virginia-ohio" {
  peer_account_id         = aws_ec2_transit_gateway.tgw-ohio.owner_id
  peer_region             = var.vpc_region_ohio
  peer_transit_gateway_id = aws_ec2_transit_gateway.tgw-ohio.id
  transit_gateway_id      = aws_ec2_transit_gateway.tgw-virginia.id
  tags = {
    Name = "tgw-peering-virginia-ohio-requestor"
  }
}
# TGW Peering between virginia & california
resource "aws_ec2_transit_gateway_peering_attachment" "tgw-peering-virginia-california" {
  peer_account_id         = aws_ec2_transit_gateway.tgw-california.owner_id
  peer_region             = var.vpc_region_california
  peer_transit_gateway_id = aws_ec2_transit_gateway.tgw-california.id
  transit_gateway_id      = aws_ec2_transit_gateway.tgw-virginia.id
  tags = {
    Name = "tgw-peering-virginia-california-requestor"
  }
}

// NOTE: aws_ec2_transit_gateway_peering_attachment_accepter is not relased yet.
// find about the latest status here: https://github.com/terraform-providers/terraform-provider-aws/pull/11185

# TGW route table routes
resource "aws_ec2_transit_gateway_route" "tgw-virginia-rt-to-ohio" {
  destination_cidr_block         = "10.2.0.0/16"
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_peering_attachment.tgw-peering-virginia-ohio.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway.tgw-virginia.association_default_route_table_id
}
resource "aws_ec2_transit_gateway_route" "tgw-virginia-rt-to-california" {
  destination_cidr_block         = "10.3.0.0/16"
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_peering_attachment.tgw-peering-virginia-california.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway.tgw-virginia.association_default_route_table_id
}
resource "aws_ec2_transit_gateway_route" "tgw-ohio-rt-to-virginia" {
  provider = aws.ohio
  destination_cidr_block         = "10.1.0.0/16"
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_peering_attachment.tgw-peering-virginia-ohio.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway.tgw-ohio.association_default_route_table_id
}
resource "aws_ec2_transit_gateway_route" "tgw-california-rt-to-virginia" {
  provider = aws.california
  destination_cidr_block         = "10.1.0.0/16"
  transit_gateway_attachment_id  = aws_ec2_transit_gateway_peering_attachment.tgw-peering-virginia-california.id
  transit_gateway_route_table_id = aws_ec2_transit_gateway.tgw-california.association_default_route_table_id
}

# TGW attachement to account
resource "aws_ec2_transit_gateway_vpc_attachment" "tgw-att-account" {
  subnet_ids         = [aws_subnet.account_tgw_subnet.id]
  depends_on         = [aws_subnet.account_tgw_subnet]
  transit_gateway_id = aws_ec2_transit_gateway.tgw-virginia.id
  vpc_id             = aws_vpc.account.id
  tags               = {
    Name = format("tgw-att-account")
  }
}
# TGW attachement to different
resource "aws_ec2_transit_gateway_vpc_attachment" "tgw-att-different" {
  provider = aws.ohio
  subnet_ids         = [aws_subnet.different_tgw_subnet.id]
  depends_on         = [aws_subnet.different_tgw_subnet]
  transit_gateway_id = aws_ec2_transit_gateway.tgw-ohio.id
  vpc_id             = aws_vpc.different.id
  tags               = {
    Name = format("tgw-att-different")
  }
}
# TGW attachement to same
resource "aws_ec2_transit_gateway_vpc_attachment" "tgw-att-same" {
  provider = aws.california
  subnet_ids         = [aws_subnet.same_tgw_subnet.id]
  depends_on         = [aws_subnet.same_tgw_subnet]
  transit_gateway_id = aws_ec2_transit_gateway.tgw-california.id
  vpc_id             = aws_vpc.same.id
  tags               = {
    Name = format("tgw-att-same")
  }
}
