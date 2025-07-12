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

##################################### VPC jump ###################################
#################### VPC jump vars ####################
# `jump` is the vpc keyword being used for tagging in all resources belongs to this vpc.
# replace `jump` with your prefered name.

variable "jump" {
  description = "VPC Name"
  default     = "jump"
}
variable "jump_cidr" {
  description = "CIDR block for the VPC"
  default     = "10.1.0.0/16"
}
variable "jump_public_subnet" {
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

#################### igw-ngw ####################
# Define igw
resource "aws_internet_gateway" "jump_igw" {
  vpc_id     = aws_vpc.jump.id
  tags = {
    Name = format("jump_igw")
  }
}

#################### route tables ####################
# Define route table - igw
resource "aws_route_table" "jump_rtb_igw" {
  vpc_id = aws_vpc.jump.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.jump_igw.id
  }
  route {
    cidr_block = "10.2.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-jump-targets_instance-r.id
  }
  tags = {
    Name = format("%s_rtb_igw", var.jump)
  }
}
# associate route table to jump_public_subnet
resource "aws_route_table_association" "jump_rtb_asctn_jump_public_subnet" {
  route_table_id = aws_route_table.jump_rtb_igw.id
  subnet_id      = aws_subnet.jump_public_subnet.id
}

############# security-group #############
# Define security-group
resource "aws_security_group" "jump_sg_general" {
  name = "jump_sg_general"
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
    Name =  format("%s_general", var.jump)
  }
}
############# NACL #############
resource "aws_network_acl" "jump_nacl_general" {
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
    Name =  format("%s_general", var.jump)
  }
}

################## instances ####################
# Create EC2 linux instance - jump
resource "aws_instance" "jump_host" {
  count = 1
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = "10.1.1.100"
  subnet_id                   = aws_subnet.jump_public_subnet.id
  vpc_security_group_ids      = [aws_security_group.jump_sg_general.id]
  user_data = file(var.update-server)
  tags = {
    Name =  format("jump_host%s",count.index+1)
  }
}



##################################### VPC targets_instance ###################################
#################### VPC targets_instance vars ####################
# `targets_instance` is the vpc keyword being used for tagging in all resources belongs to this vpc.
# replace `targets_instance` with your prefered name.

variable "targets_instance" {
  description = "VPC Name"
  default     = "targets_instance"
}
variable "targets_instance_cidr" {
  description = "CIDR block for the VPC"
  default     = "10.2.0.0/16"
}
variable "targets_instance_public_subnet" {
  description = "public subnet"
  default     = "10.2.1.0/24"
}
variable "targets_instance_private_subnet" {
  description = "same subnet"
  default     = "10.2.101.0/24"
}

#################### vpc ####################
# Define VPC
resource "aws_vpc" "targets_instance" {
  cidr_block = var.targets_instance_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = var.targets_instance
  }
}

############# Subnets #############
# Define public subnet
resource "aws_subnet" "targets_instance_public_subnet" {
  vpc_id     = aws_vpc.targets_instance.id
  cidr_block = var.targets_instance_public_subnet
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.targets_instance, var.targets_instance_public_subnet)
  }
}
# Define targets_instance_private_subnet
resource "aws_subnet" "targets_instance_private_subnet" {
  vpc_id     = aws_vpc.targets_instance.id
  cidr_block = var.targets_instance_private_subnet
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.targets_instance, var.targets_instance_private_subnet)
  }
}

#################### igw-ngw ####################
# Define igw
resource "aws_internet_gateway" "targets_instance_igw" {
  vpc_id     = aws_vpc.targets_instance.id
  tags = {
    Name = format("targets_instance_igw")
  }
}
# Define elastic ip for ngw
resource "aws_eip" "targets_instance_ngw_eip" {
  vpc = true
    tags = {
    Name = format("targets_instance_ngw_eip")
  }
}
# Define ngw
resource "aws_nat_gateway" "targets_instance_ngw" {
  allocation_id = aws_eip.targets_instance_ngw_eip.id
  subnet_id     = aws_subnet.targets_instance_public_subnet.id
  depends_on = [aws_internet_gateway.targets_instance_igw]
    tags = {
    Name = format("targets_instance_ngw")
  }
}

#################### route tables ####################
# Define route table - igw
resource "aws_route_table" "targets_instance_rtb_igw" {
  vpc_id = aws_vpc.targets_instance.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.targets_instance_igw.id
  }
  tags = {
    Name = format("%s_rtb_igw", var.targets_instance)
  }
}
# associate route table to targets_instance_public_subnet
resource "aws_route_table_association" "targets_instance_rtb_asctn_targets_instance_public_subnet" {
  route_table_id = aws_route_table.targets_instance_rtb_igw.id
  subnet_id      = aws_subnet.targets_instance_public_subnet.id
}

# Define route table  - ngw
resource "aws_route_table" "targets_instance_rtb_ngw" {
  vpc_id = aws_vpc.targets_instance.id
  route {
    cidr_block = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.targets_instance_ngw.id
  }
  route {
    cidr_block = "10.1.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-jump-targets_instance-r.id
  }
}
# associate route table to targets_instance_private_subnet
resource "aws_route_table_association" "targets_instance_rtb_asctn_targets_instance_private_subnet" {
  route_table_id = aws_route_table.targets_instance_rtb_ngw.id
  subnet_id      = aws_subnet.targets_instance_private_subnet.id
}

############# security-group #############
# Define security-group
resource "aws_security_group" "targets_instance_pri_pub_a_sg" {
  name = "targets_instance_pri_pub_a_sg"
  vpc_id = aws_vpc.targets_instance.id
  # SSH access is controlled at NACL
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
      cidr_blocks = ["10.2.1.99/32", "8.8.8.8/32", "67.160.71.197/32"]
      description = "HTTP Access"
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
    Name =  format("%s_pri_pub_a", var.targets_instance)
  }
}
############# NACL #############
resource "aws_network_acl" "targets_instance_nlb_nacl" {
  vpc_id = aws_vpc.targets_instance.id
  subnet_ids = [
    aws_subnet.targets_instance_public_subnet.id
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
    Name =  format("%s_nlb", var.targets_instance)
  }
}
resource "aws_network_acl" "targets_instance_target_nacl" {
  vpc_id = aws_vpc.targets_instance.id
  subnet_ids = [
    aws_subnet.targets_instance_private_subnet.id
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
    Name =  format("%s_target", var.targets_instance)
  }
}

################# instances ####################
# Create EC2 linux instance - targets_instance_pri_pub_a
resource "aws_instance" "targets_instance_pri_pub_a" {
  count = 1
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = format("10.2.101.10%s", count.index)
  subnet_id                   = aws_subnet.targets_instance_private_subnet.id
  vpc_security_group_ids      = [aws_security_group.targets_instance_pri_pub_a_sg.id]
  user_data = file(var.create-web-server)
  tags = {
    Name =  format("targets_instance_pri_pub_a%s",count.index+1)
  }
}


#################### NLB ####################
# Define elastic ip for nlb
resource "aws_eip" "targets_instance_nlb_eip_pri_pub_a" {
  vpc = true
    tags = {
    Name = format("targets_instance_nlb_eip_pri_pub_a")
  }
}
resource "aws_lb" "targets_instance_nlb_pri_pub_a" {
  name = "targets-instance-nlb-pri-pub-a"
  internal           = false
  load_balancer_type = "network"
  subnet_mapping {
  subnet_id     = aws_subnet.targets_instance_public_subnet.id
  allocation_id = aws_eip.targets_instance_nlb_eip_pri_pub_a.id
  }
}
resource "aws_lb_target_group" "targets_instance_nlb_tg_pri_pub_a" {
  name = "targets-instance-tg-pri-pub-a"
  port     = 80
  protocol = "TCP"
  vpc_id = aws_vpc.targets_instance.id
}
resource "aws_lb_listener" "targets_instance_nlb_lsnr_pri_pub_a" {
  load_balancer_arn = aws_lb.targets_instance_nlb_pri_pub_a.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.targets_instance_nlb_tg_pri_pub_a.arn
  }
}
resource "aws_lb_target_group_attachment" "targets_instance_nlb_tg_att_pri_pub_a" {
  count = 1
  target_group_arn = aws_lb_target_group.targets_instance_nlb_tg_pri_pub_a.arn
  target_id        = aws_instance.targets_instance_pri_pub_a[count.index].id
  port             = 80
}


#################### VPC Peering ####################
# jump to targets_instance - requester
resource "aws_vpc_peering_connection" "pcx-jump-targets_instance-r" {
  vpc_id        = aws_vpc.jump.id
  peer_vpc_id   = aws_vpc.targets_instance.id
  peer_owner_id = data.aws_caller_identity.requester.account_id
  auto_accept   = true
  tags = {
    Name = "pcx-jump-targets_instance-r"
  }
}



#################### only_pub_a ####################
# Define security-group
resource "aws_security_group" "targets_instance_only_pub_a_sg" {
  name = "targets_instance_only_pub_a_sg"
  vpc_id = aws_vpc.targets_instance.id
  # SSH access is controlled at NACL
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
      cidr_blocks = ["8.8.8.8/32", "67.160.71.197/32"]
      description = "HTTP Access"
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
    Name =  format("%s_only_pub_a", var.targets_instance)
  }
}

################## instances ####################
# Create EC2 linux instance - targets_instance_only_pub_a
resource "aws_instance" "targets_instance_only_pub_a" {
  count = 1
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = format("10.2.101.11%s", count.index)
  subnet_id                   = aws_subnet.targets_instance_private_subnet.id
  vpc_security_group_ids      = [aws_security_group.targets_instance_only_pub_a_sg.id]
  user_data = file(var.create-web-server)
  tags = {
    Name =  format("targets_instance_only_pub_a%s",count.index+1)
  }
}

#################### NLB ####################
# Define elastic ip for nlb
resource "aws_eip" "targets_instance_nlb_eip_only_pub_a" {
  vpc = true
    tags = {
    Name = format("targets_instance_nlb_eip_only_pub_a")
  }
}
resource "aws_lb" "targets_instance_nlb_only_pub_a" {
  name = "targets-instance-nlb-only-pub-a"
  internal           = false
  load_balancer_type = "network"
  subnet_mapping {
  subnet_id     = aws_subnet.targets_instance_public_subnet.id
  allocation_id = aws_eip.targets_instance_nlb_eip_only_pub_a.id
  }
  tags = {
    Name =  format("targets_instance_nlb_only_pub_a")
  }
}
resource "aws_lb_target_group" "targets_instance_nlb_tg_only_pub_a" {
  name = "targets-instance-tg-only-pub-a"
  port     = 80
  protocol = "TCP"
  vpc_id = aws_vpc.targets_instance.id
}
resource "aws_lb_listener" "targets_instance_nlb_lsnr_only_pub_a" {
  load_balancer_arn = aws_lb.targets_instance_nlb_only_pub_a.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.targets_instance_nlb_tg_only_pub_a.arn
  }
}
resource "aws_lb_target_group_attachment" "targets_instance_nlb_tg_att_only_pub_a" {
  count = 1
  target_group_arn = aws_lb_target_group.targets_instance_nlb_tg_only_pub_a.arn
  target_id        = aws_instance.targets_instance_only_pub_a[count.index].id
  port             = 80
}


#################### only_pri_a ####################
# Define security-group
resource "aws_security_group" "targets_instance_only_pri_a_sg" {
  name = "targets_instance_only_pri_a_sg"
  vpc_id = aws_vpc.targets_instance.id
  # SSH access is controlled at NACL
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
      cidr_blocks = ["10.2.1.32/32"]
      description = "HTTP Access"
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
    Name =  format("%s_only_pri_a", var.targets_instance)
  }
}

################## instances ####################
# Create EC2 linux instance - targets_instance_only_pri_a
resource "aws_instance" "targets_instance_only_pri_a" {
  count = 1
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = format("10.2.101.12%s", count.index)
  subnet_id                   = aws_subnet.targets_instance_private_subnet.id
  vpc_security_group_ids      = [aws_security_group.targets_instance_only_pri_a_sg.id]
  user_data = file(var.create-web-server)
  tags = {
    Name =  format("targets_instance_only_pri_a%s",count.index+1)
  }
}

#################### NLB ####################
# Define elastic ip for nlb
resource "aws_eip" "targets_instance_nlb_eip_only_pri_a" {
  vpc = true
    tags = {
    Name = format("targets_instance_nlb_eip_only_pri_a")
  }
}
resource "aws_lb" "targets_instance_nlb_only_pri_a" {
  name = "targets-instance-nlb-only-pri-a"
  internal           = false
  load_balancer_type = "network"
  subnet_mapping {
  subnet_id     = aws_subnet.targets_instance_public_subnet.id
  allocation_id = aws_eip.targets_instance_nlb_eip_only_pri_a.id
  }
  tags = {
    Name =  format("targets_instance_nlb_only_pri_a")
  }
}
resource "aws_lb_target_group" "targets_instance_nlb_tg_only_pri_a" {
  name = "targets-instance-tg-only-pri-a"
  port     = 80
  protocol = "TCP"
  vpc_id = aws_vpc.targets_instance.id
  tags = {
    Name =  format("targets_instance_nlb_tg_only_pri_a")
  }
}
resource "aws_lb_listener" "targets_instance_nlb_lsnr_only_pri_a" {
  load_balancer_arn = aws_lb.targets_instance_nlb_only_pri_a.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.targets_instance_nlb_tg_only_pri_a.arn
  }
}
resource "aws_lb_target_group_attachment" "targets_instance_nlb_tg_att_only_pri_a" {
  count = 1
  target_group_arn = aws_lb_target_group.targets_instance_nlb_tg_only_pri_a.arn
  target_id        = aws_instance.targets_instance_only_pri_a[count.index].id
  port             = 80
}
