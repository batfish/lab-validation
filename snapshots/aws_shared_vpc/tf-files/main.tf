
##################################### VPC shared_services ###################################
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

#################### shared_services ####################
# `shared_services` is the vpc keyword being used for tagging in all resources belongs to this vpc.
# replace `shared_services` with your prefered name.

variable "shared_services" {
  description = "VPC Name"
  default     = "shared_services"
}
variable "shared_services_cidr" {
  description = "CIDR block for the VPC"
  default     = "10.1.0.0/16"
}
variable "shared_services_shared_subnet" {
  description = "shred subnet"
  default     = "10.1.1.0/24"
}
variable "shared_services_non_shared_subnet" {
  description = "non_shared subnet"
  default     = "10.1.2.0/24"
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
resource "aws_vpc" "shared_services" {
  cidr_block = var.shared_services_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = var.shared_services
  }
}

############# Subnets #############
# Define shared subnet
resource "aws_subnet" "shared_services_shared_subnet" {
  vpc_id     = aws_vpc.shared_services.id
  cidr_block = var.shared_services_shared_subnet
  map_public_ip_on_launch = "true"
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.shared_services, var.shared_services_shared_subnet)
  }
}
# Define non_shared subnet
resource "aws_subnet" "shared_services_non_shared_subnet" {
  vpc_id     = aws_vpc.shared_services.id
  cidr_block = var.shared_services_non_shared_subnet
  map_public_ip_on_launch = "true"
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.shared_services, var.shared_services_non_shared_subnet)
  }
}

#################### igw-ngw ####################
# Define igw
resource "aws_internet_gateway" "shareds_services_igw" {
  vpc_id     = aws_vpc.shared_services.id
  tags = {
    Name = format("shareds_services_igw")
  }
}

#################### route tables ####################
# Define route table
resource "aws_route_table" "shared_services_rtb" {
  vpc_id = aws_vpc.shared_services.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.shareds_services_igw.id
  }
  route {
    cidr_block = "10.4.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-jump-shared_services-r.id
  }
  tags = {
    Name = format("%s-rtb", var.shared_services)
  }
}
# associate route table to the shared subnet
resource "aws_route_table_association" "shared_services_rtb_asctn_shared" {
  route_table_id = aws_route_table.shared_services_rtb.id
  subnet_id      = aws_subnet.shared_services_shared_subnet.id
}
# associate route table to the non_shared subnet
resource "aws_route_table_association" "shared_services_rtb_asctn_non_shared" {
  route_table_id = aws_route_table.shared_services_rtb.id
  subnet_id      = aws_subnet.shared_services_non_shared_subnet.id
}
############# security-group #############
# Define security-group
resource "aws_security_group" "shared_services_shared" {
  name = "shared_services_shared"
  vpc_id = aws_vpc.shared_services.id
  # SSH access is controlled at NACL
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all"
  }
  tags = {
    Name =  format("%s-shared", var.shared_services)
  }
}
resource "aws_security_group_rule" "shared_services_shared_allow_ssh" {
    type = "ingress"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    security_group_id = aws_security_group.shared_services_shared.id
    description = "SSH Access"
}
resource "aws_security_group_rule" "shared_services_shared_allow_icmp_cidr" {
    type = "ingress"
    from_port   = 8
    to_port     = 0
    protocol    = "icmp"
    cidr_blocks = ["10.4.1.100/32"]
    security_group_id = aws_security_group.shared_services_shared.id
    description = "ICMP Echo Request Access"
}
resource "aws_security_group_rule" "shared_services_shared_allow_icmp_sg_prod" {
    type = "ingress"
    from_port   = 8
    to_port     = 0
    protocol    = "icmp"
    security_group_id = aws_security_group.shared_services_shared.id
    source_security_group_id = aws_security_group.shared_services_prod.id
    description = "ICMP Echo Request Access"
}
resource "aws_security_group_rule" "shared_services_shared_allow_icmp_sg_dev" {
    type = "ingress"
    from_port   = 8
    to_port     = 0
    protocol    = "icmp"
    security_group_id = aws_security_group.shared_services_shared.id
    source_security_group_id = aws_security_group.shared_services_dev.id
    description = "ICMP Echo Request Access"
}
resource "aws_security_group_rule" "shared_services_shared_allow_traceroute" {
    type = "ingress"
    from_port   = 33434
    to_port     = 33534
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    security_group_id = aws_security_group.shared_services_shared.id
    description = "Traceroute Access"
}

resource "aws_security_group" "shared_services_non_shared" {
  name = "shared_services_non_shared"
  vpc_id = aws_vpc.shared_services.id
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
      cidr_blocks = ["10.4.1.100/32"]
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
    Name =  format("%s-non_shared", var.shared_services)
  }
}
############# NACL #############
resource "aws_network_acl" "shared_services_nacl" {
  vpc_id = aws_vpc.shared_services.id
  subnet_ids = [
    aws_subnet.shared_services_shared_subnet.id,
    aws_subnet.shared_services_non_shared_subnet.id
  ]
  ingress {
    protocol   = "tcp"
    rule_no    = 10
    action     = "allow"
    cidr_block = "10.4.1.100/32"
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
    Name =  format("%s-general", var.shared_services)
  }
}

################## instances ####################
# Create EC2 linux instance shared01
resource "aws_instance" "shared_services_shared01" {
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = "10.1.1.100"
  subnet_id                   = aws_subnet.shared_services_shared_subnet.id
  vpc_security_group_ids      = [aws_security_group.shared_services_shared.id]
  user_data = file(var.update-server)
  tags = {
    Name =  format("%s-shared01", var.shared_services)
  }
}
# Create EC2 linux instance non_shared01
resource "aws_instance" "shared_services_non_shared01" {
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = "10.1.2.100"
  subnet_id                   = aws_subnet.shared_services_non_shared_subnet.id
  vpc_security_group_ids      = [aws_security_group.shared_services_non_shared.id]
  user_data = file(var.update-server)
  tags = {
    Name =  format("%s-non-shared01", var.shared_services)
  }
}


##################################### VPC prod ###################################
#################### common ####################
# change profile as necessary. Generally profile is "default"
variable "profile_2" {
  description = "account profile"
  default     = "Sandbox2Admin"
}
data "aws_caller_identity" "prod" {
    provider = aws.prod
}
output "account_id_prod" {
  value = data.aws_caller_identity.prod.account_id
}
#################### prod ####################
# `prod` is the vpc keyword being used for tagging in all resources belongs to this vpc.
# replace `prod` with your prefered name.

variable "prod" {
  description = "VPC Name"
  default     = "prod"
}
variable "prod_cidr" {
  description = "CIDR block for the VPC"
  default     = "10.2.0.0/16"
}
variable "prod_non_shared_subnet" {
  description = "non_shared subnet"
  default     = "10.2.1.0/24"
}

#################### Provider Config ####################
provider "aws" {
  alias = "prod"
  profile = var.profile_2
  region  = var.vpc_region_ohio
}
# Use existing ssh key pair
resource "aws_key_pair" "ec2key_2" {
  provider = aws.prod
  key_name = "publicKey"
  public_key = file(var.public_key_path)
}
#################### vpc ####################
# Define VPC
resource "aws_vpc" "prod" {
  provider = aws.prod
  cidr_block = var.prod_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = var.prod
  }
}

############# Subnets #############
# Define non_shared subnet
resource "aws_subnet" "prod_non_shared_subnet" {
  provider = aws.prod
  vpc_id     = aws_vpc.prod.id
  cidr_block = var.prod_non_shared_subnet
  map_public_ip_on_launch = "true"
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.prod, var.prod_non_shared_subnet)
  }
}

#################### igw-ngw ####################
# Define igw
resource "aws_internet_gateway" "prod_igw" {
  provider = aws.prod
  vpc_id     = aws_vpc.prod.id
  tags = {
    Name = format("prod_igw")
  }
}

#################### route tables ####################
# Define route table  - non_shared
resource "aws_route_table" "prod_rtb_non_shared" {
  provider = aws.prod
  vpc_id = aws_vpc.prod.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.prod_igw.id
  }
  route {
    cidr_block = "10.4.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-jump-prod-r.id
  }
  tags = {
    Name = format("%s-non_shared", var.prod)
  }
}
# associate igw route table to non_shared subnet
resource "aws_route_table_association" "prod-rtb-asctn-igw-public" {
  provider = aws.prod
  route_table_id = aws_route_table.prod_rtb_non_shared.id
  subnet_id      = aws_subnet.prod_non_shared_subnet.id
}

############# security-group #############
# Define security-group
resource "aws_security_group" "prod_sg" {
  provider = aws.prod
  name = "prod_sg"
  vpc_id = aws_vpc.prod.id
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
      cidr_blocks = ["10.4.1.100/32"]
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
    Name =  format("%s-general", var.prod)
  }
}
############# NACL #############
resource "aws_network_acl" "prod_nacl" {
  provider = aws.prod
  vpc_id = aws_vpc.prod.id
  subnet_ids = [
    aws_subnet.prod_non_shared_subnet.id
  ]
  ingress {
    protocol   = "tcp"
    rule_no    = 10
    action     = "allow"
    cidr_block = "10.4.1.100/32"
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
    Name =  format("%s-general", var.prod)
  }
}

################## instances ####################
# Create EC2 linux instance prod_non_shared01
resource "aws_instance" "prod_non_shared01" {
  provider = aws.prod
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key_2.key_name
  subnet_id                   = aws_subnet.prod_non_shared_subnet.id
  private_ip                  = "10.2.1.100"
  vpc_security_group_ids      = [aws_security_group.prod_sg.id]
  user_data = file(var.update-server)
  tags = {
    Name =  format("%s-non_shared01", var.prod)
  }
}



##################################### VPC dev ###################################
#################### common ####################
# change profile as necessary. Generally profile is "default"
variable "profile_3" {
  description = "account profile"
  default     = "Sandbox3Admin"
}
data "aws_caller_identity" "dev" {
    provider = aws.dev
}
output "account_id_dev" {
  value = data.aws_caller_identity.dev.account_id
}
#################### dev ####################
# `dev` is the vpc keyword being used for tagging in all resources belongs to this vpc.
# replace `dev` with your prefered name.

variable "dev" {
  description = "VPC Name"
  default     = "dev"
}
variable "dev_cidr" {
  description = "CIDR block for the VPC"
  default     = "10.3.0.0/16"
}
variable "dev_non_shared_subnet" {
  description = "non_shared subnet"
  default     = "10.3.1.0/24"
}

#################### Provider Config ####################
provider "aws" {
  alias = "dev"
  profile = var.profile_3
  region  = var.vpc_region_ohio
}
# Use existing ssh key pair
resource "aws_key_pair" "ec2key_3" {
  provider = aws.dev
  key_name = "publicKey"
  public_key = file(var.public_key_path)
}
#################### vpc ####################
# Define VPC
resource "aws_vpc" "dev" {
  provider = aws.dev
  cidr_block = var.dev_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = var.dev
  }
}

############# Subnets #############
# Define non_shared subnet
resource "aws_subnet" "dev_non_shared_subnet" {
  provider = aws.dev
  vpc_id     = aws_vpc.dev.id
  cidr_block = var.dev_non_shared_subnet
  map_public_ip_on_launch = "true"
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.dev, var.dev_non_shared_subnet)
  }
}

#################### igw-ngw ####################
# Define igw
resource "aws_internet_gateway" "dev_igw" {
  provider = aws.dev
  vpc_id     = aws_vpc.dev.id
  tags = {
    Name = format("dev_igw")
  }
}

#################### route tables ####################
# Define route table  - non_shared
resource "aws_route_table" "dev_rtb_non_shared" {
  provider = aws.dev
  vpc_id = aws_vpc.dev.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.dev_igw.id
  }
  route {
    cidr_block = "10.4.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-jump-dev-r.id
  }
  tags = {
    Name = format("%s-non_shared", var.dev)
  }
}
# associate igw route table to non_shared subnet
resource "aws_route_table_association" "dev-rtb-asctn-igw-public" {
  provider = aws.dev
  route_table_id = aws_route_table.dev_rtb_non_shared.id
  subnet_id      = aws_subnet.dev_non_shared_subnet.id
}

############# security-group #############
# Define security-group
resource "aws_security_group" "dev_sg" {
  provider = aws.dev
  name = "dev_sg"
  vpc_id = aws_vpc.dev.id
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
      cidr_blocks = ["10.4.1.100/32"]
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
    Name =  format("%s-general", var.dev)
  }
}
############# NACL #############
resource "aws_network_acl" "dev_nacl" {
  provider = aws.dev
  vpc_id = aws_vpc.dev.id
  subnet_ids = [
    aws_subnet.dev_non_shared_subnet.id
  ]
  ingress {
    protocol   = "tcp"
    rule_no    = 10
    action     = "allow"
    cidr_block = "10.4.1.100/32"
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
    Name =  format("%s-general", var.dev)
  }
}

################## instances ####################
# Create EC2 linux instance dev_non_shared01
resource "aws_instance" "dev_non_shared01" {
  provider = aws.dev
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key_2.key_name
  subnet_id                   = aws_subnet.dev_non_shared_subnet.id
  private_ip                  = "10.3.1.100"
  vpc_security_group_ids      = [aws_security_group.dev_sg.id]
  user_data = file(var.update-server)
  tags = {
    Name =  format("%s-non_shared01", var.dev)
  }
}



##################################### VPC jump ###################################
# `jump` is the vpc keyword being used for tagging in all resources belongs to this vpc.
# replace `jump` with your prefered name.

variable "jump" {
  description = "VPC Name"
  default     = "jump"
}
variable "jump_cidr" {
  description = "CIDR block for the VPC"
  default     = "10.4.0.0/16"
}
variable "jump_public_subnet" {
  description = "public subnet"
  default     = "10.4.1.0/24"
}

#################### vpc ####################
# Define VPC
resource "aws_vpc" "jump" {
  cidr_block = var.jump_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = var.jump
  }
}

############# Subnets #############
# Define public subnet
resource "aws_subnet" "jump_public_subnet" {
  vpc_id     = aws_vpc.jump.id
  cidr_block = var.jump_public_subnet
  map_public_ip_on_launch = "true"
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.jump, var.jump_public_subnet)
  }
}

############# gateways #############
# Define internet gateway
resource "aws_internet_gateway" "jump_igw" {
  vpc_id = aws_vpc.jump.id
  tags = {
    Name = format("jump-%s", var.jump)
  }
}
#################### route tables ####################
# Define route table  - igw
resource "aws_route_table" "jump_rtb_igw" {
  vpc_id = aws_vpc.jump.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.jump_igw.id
  }
  route {
    cidr_block = "10.1.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-jump-shared_services-r.id
  }
  route {
    cidr_block = "10.2.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-jump-prod-r.id
  }
  route {
    cidr_block = "10.3.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-jump-dev-r.id
  }
  tags = {
    Name = format("%s-rtb-igw", var.jump)
  }
}
# associate igw route table to the public subnet
resource "aws_route_table_association" "jump_rtb_igw_asctn_jump" {
  route_table_id = aws_route_table.jump_rtb_igw.id
  subnet_id      = aws_subnet.jump_public_subnet.id
}

############# security-group #############
# Define security-group
resource "aws_security_group" "jump_sg" {
  name = "jump_sg"
  vpc_id = aws_vpc.jump.id
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
    Name =  format("%s-general", var.jump)
  }
}
############# NACL #############
resource "aws_network_acl" "jump_nacl" {
  vpc_id = aws_vpc.jump.id
  subnet_ids = [
    aws_subnet.jump_public_subnet.id
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
    Name =  format("%s-general", var.jump)
  }
}

################### instances ####################
# Create EC2 linux instance jump01
resource "aws_instance" "jump01" {
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = "10.4.1.100"
  subnet_id                   = aws_subnet.jump_public_subnet.id
  vpc_security_group_ids      = [aws_security_group.jump_sg.id]
  user_data = file(var.update-server)
  tags = {
    Name =  format("%s-01", var.jump)
  }
}



#################### VPC Peering ####################
# jump to shared_services - requester
resource "aws_vpc_peering_connection" "pcx-jump-shared_services-r" {
  vpc_id        = aws_vpc.jump.id
  peer_vpc_id   = aws_vpc.shared_services.id
  peer_owner_id = data.aws_caller_identity.requester.account_id
  auto_accept   = true
  tags = {
    Name = "pcx-jump-shared_services-r"
  }
}
# jump to prod - requester
resource "aws_vpc_peering_connection" "pcx-jump-prod-r" {
  vpc_id        = aws_vpc.jump.id
  peer_vpc_id   = aws_vpc.prod.id
  peer_owner_id = data.aws_caller_identity.prod.account_id
  auto_accept   = false
  tags = {
    Name = "pcx-jump-prod-r"
  }
}
# jump to prod - accepter
resource "aws_vpc_peering_connection_accepter" "pcx-prod-jump-a" {
  provider = aws.prod
  vpc_peering_connection_id = aws_vpc_peering_connection.pcx-jump-prod-r.id
  auto_accept               = true
  tags = {
    Name = "pcx-prod-jump-a"
  }
}
# jump to dev - requester
resource "aws_vpc_peering_connection" "pcx-jump-dev-r" {
  vpc_id        = aws_vpc.jump.id
  peer_vpc_id   = aws_vpc.dev.id
  peer_owner_id = data.aws_caller_identity.dev.account_id
  auto_accept   = false
  tags = {
    Name = "pcx-jump-dev-r"
  }
}
# jump to dev - accepter
resource "aws_vpc_peering_connection_accepter" "pcx-dev-jump-a" {
  provider = aws.dev
  vpc_peering_connection_id = aws_vpc_peering_connection.pcx-jump-dev-r.id
  auto_accept               = true
  tags = {
    Name = "pcx-dev-jump-a"
  }
}



# #################### shared subnet ####################
# Create RAM - subnet
resource "aws_ram_resource_share" "shared-services-ram-subnet" {
  name = "shared-services-ram-subnet"
  #allow_external_principals = true
  tags = {
    Name = "shared-services-ram-subnet"
  }
}
# Associate RAM with subnet
resource "aws_ram_resource_association" "shared-services-ram-subnet-asctn" {
  resource_arn       = aws_subnet.shared_services_shared_subnet.arn
  resource_share_arn = aws_ram_resource_share.shared-services-ram-subnet.arn
}
# Share subnet with prod vpc owner
resource "aws_ram_principal_association" "shared-services-ram-principal-asctn-prod" {
  principal          = data.aws_caller_identity.prod.account_id
  resource_share_arn = aws_ram_resource_share.shared-services-ram-subnet.arn
}
# Share subnet with dev vpc owner
resource "aws_ram_principal_association" "shared-services-ram-principal-asctn-dev" {
  principal          = data.aws_caller_identity.dev.account_id
  resource_share_arn = aws_ram_resource_share.shared-services-ram-subnet.arn
}


############################## Create SG and instance in shared enviornment #####################################
# Define security-group for vpc prod in shared services subnet
resource "aws_security_group" "shared_services_prod" {
  name = "shared_services_prod"
  provider = aws.prod
  vpc_id = aws_vpc.shared_services.id
  # SSH access is controlled at NACL
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all"
  }
  tags = {
    Name =  format("shared_services_prod")
  }
}
resource "aws_security_group_rule" "shared_services_prod_allow_ssh" {
    provider = aws.prod
    type = "ingress"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    security_group_id = aws_security_group.shared_services_prod.id
    description = "SSH Access"
}
resource "aws_security_group_rule" "shared_services_prod_allow_icmp_cidr" {
    provider = aws.prod
    type = "ingress"
    from_port   = 8
    to_port     = 0
    protocol    = "icmp"
    cidr_blocks = ["10.4.1.100/32"]
    security_group_id = aws_security_group.shared_services_prod.id
    description = "ICMP Echo Request Access"
}
resource "aws_security_group_rule" "shared_services_prod_allow_icmp_sg_shared_services" {
    provider = aws.prod
    type = "ingress"
    from_port   = 8
    to_port     = 0
    protocol    = "icmp"
    security_group_id = aws_security_group.shared_services_prod.id
    source_security_group_id = aws_security_group.shared_services_shared.id
    description = "ICMP Echo Request Access"
}
resource "aws_security_group_rule" "shared_services_prod_allow_icmp_sg_dev" {
    provider = aws.prod
    type = "ingress"
    from_port   = 8
    to_port     = 0
    protocol    = "icmp"
    security_group_id = aws_security_group.shared_services_prod.id
    source_security_group_id = aws_security_group.shared_services_dev.id
    description = "ICMP Echo Request Access"
}
resource "aws_security_group_rule" "shared_services_prod_allow_traceroute" {
    provider = aws.prod
    type = "ingress"
    from_port   = 33434
    to_port     = 33534
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    security_group_id = aws_security_group.shared_services_prod.id
    description = "Traceroute Access"
}

# Create EC2 linux instance by vpc prod owner into shared services subnet
resource "aws_instance" "prod_shared01" {
  provider = aws.prod
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key_2.key_name
  private_ip                  = "10.1.1.101"
  subnet_id                   = aws_subnet.shared_services_shared_subnet.id
  vpc_security_group_ids      = [aws_security_group.shared_services_prod.id]
  user_data = file(var.update-server)
  tags = {
    Name =  format("%s-shared01", var.prod)
  }
}


# Define security-group for vpc dev in shared services subnet
resource "aws_security_group" "shared_services_dev" {
  name = "shared_services_dev"
  provider = aws.dev
  vpc_id = aws_vpc.shared_services.id
  # SSH access is controlled at NACL
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all"
  }
  tags = {
    Name =  format("shared_services_dev")
  }
}
resource "aws_security_group_rule" "shared_services_dev_allow_ssh" {
    provider = aws.dev
    type = "ingress"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    security_group_id = aws_security_group.shared_services_dev.id
    description = "SSH Access"
}
resource "aws_security_group_rule" "shared_services_dev_allow_icmp_cidr" {
    provider = aws.dev
    type = "ingress"
    from_port   = 8
    to_port     = 0
    protocol    = "icmp"
    cidr_blocks = ["10.4.1.100/32"]
    security_group_id = aws_security_group.shared_services_dev.id
    description = "ICMP Echo Request Access"
}
resource "aws_security_group_rule" "shared_services_dev_allow_icmp_sg_dev" {
    provider = aws.dev
    type = "ingress"
    from_port   = 8
    to_port     = 0
    protocol    = "icmp"
    security_group_id = aws_security_group.shared_services_dev.id
    source_security_group_id = aws_security_group.shared_services_shared.id
    description = "ICMP Echo Request Access"
}
resource "aws_security_group_rule" "shared_services_dev_allow_icmp_sg_prod" {
    provider = aws.dev
    type = "ingress"
    from_port   = 8
    to_port     = 0
    protocol    = "icmp"
    security_group_id = aws_security_group.shared_services_dev.id
    source_security_group_id = aws_security_group.shared_services_prod.id
    description = "ICMP Echo Request Access"
}
resource "aws_security_group_rule" "shared_services_dev_allow_traceroute" {
    provider = aws.dev
    type = "ingress"
    from_port   = 33434
    to_port     = 33534
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    security_group_id = aws_security_group.shared_services_dev.id
    description = "Traceroute Access"
}

# Create EC2 linux instance by vpc dev owner into shared services subnet
resource "aws_instance" "dev_shared01" {
  provider = aws.dev
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key_2.key_name
  private_ip                  = "10.1.1.102"
  subnet_id                   = aws_subnet.shared_services_shared_subnet.id
  vpc_security_group_ids      = [aws_security_group.shared_services_dev.id]
  user_data = file(var.update-server)
  tags = {
    Name =  format("%s-shared01", var.dev)
  }
}
