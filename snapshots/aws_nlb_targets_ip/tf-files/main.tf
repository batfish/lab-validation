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
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-jump-targets_ip-r.id
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



##################################### VPC targets_ip ###################################
#################### VPC targets_ip vars ####################
# `targets_ip` is the vpc keyword being used for tagging in all resources belongs to this vpc.
# replace `targets_ip` with your prefered name.

variable "targets_ip" {
  description = "VPC Name"
  default     = "targets_ip"
}
variable "targets_ip_cidr" {
  description = "CIDR block for the VPC"
  default     = "10.2.0.0/16"
}
variable "targets_ip_public_subnet" {
  description = "public subnet"
  default     = "10.2.1.0/24"
}
variable "targets_ip_private_subnet" {
  description = "same subnet"
  default     = "10.2.101.0/24"
}

#################### vpc ####################
# Define VPC
resource "aws_vpc" "targets_ip" {
  cidr_block = var.targets_ip_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = var.targets_ip
  }
}

############# Subnets #############
# Define public subnet
resource "aws_subnet" "targets_ip_public_subnet" {
  vpc_id     = aws_vpc.targets_ip.id
  cidr_block = var.targets_ip_public_subnet
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.targets_ip, var.targets_ip_public_subnet)
  }
}
# Define targets_ip_private_subnet
resource "aws_subnet" "targets_ip_private_subnet" {
  vpc_id     = aws_vpc.targets_ip.id
  cidr_block = var.targets_ip_private_subnet
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.targets_ip, var.targets_ip_private_subnet)
  }
}

#################### igw-ngw ####################
# Define igw
resource "aws_internet_gateway" "targets_ip_igw" {
  vpc_id     = aws_vpc.targets_ip.id
  tags = {
    Name = format("targets_ip_igw")
  }
}
# Define elastic ip for ngw
resource "aws_eip" "targets_ip_ngw_eip" {
  vpc = true
    tags = {
    Name = format("targets_ip_ngw_eip")
  }
}
# Define ngw
resource "aws_nat_gateway" "targets_ip_ngw" {
  allocation_id = aws_eip.targets_ip_ngw_eip.id
  subnet_id     = aws_subnet.targets_ip_public_subnet.id
  depends_on = [aws_internet_gateway.targets_ip_igw]
    tags = {
    Name = format("targets_ip_ngw")
  }
}

#################### route tables ####################
# Define route table - igw
resource "aws_route_table" "targets_ip_rtb_igw" {
  vpc_id = aws_vpc.targets_ip.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.targets_ip_igw.id
  }
  tags = {
    Name = format("%s_rtb_igw", var.targets_ip)
  }
}
# associate route table to targets_ip_public_subnet
resource "aws_route_table_association" "targets_ip_rtb_asctn_targets_ip_public_subnet" {
  route_table_id = aws_route_table.targets_ip_rtb_igw.id
  subnet_id      = aws_subnet.targets_ip_public_subnet.id
}

# Define route table  - ngw
resource "aws_route_table" "targets_ip_rtb_ngw" {
  vpc_id = aws_vpc.targets_ip.id
  route {
    cidr_block = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.targets_ip_ngw.id
  }
  route {
    cidr_block = "10.1.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-jump-targets_ip-r.id
  }
}
# associate route table to targets_ip_private_subnet
resource "aws_route_table_association" "targets_ip_rtb_asctn_targets_ip_private_subnet" {
  route_table_id = aws_route_table.targets_ip_rtb_ngw.id
  subnet_id      = aws_subnet.targets_ip_private_subnet.id
}

############# security-group #############
# Define security-group
resource "aws_security_group" "sg_targets_ip_pd_pri_a" {
  name = "sg_targets_ip_pd_pri_a"
  vpc_id = aws_vpc.targets_ip.id
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
      cidr_blocks = ["10.2.1.194/32"]
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
    Name =  format("%s_general", var.targets_ip)
  }
}
############# NACL #############
resource "aws_network_acl" "nacl_targets_ip_general" {
  vpc_id = aws_vpc.targets_ip.id
  subnet_ids = [
    aws_subnet.targets_ip_public_subnet.id,
    aws_subnet.targets_ip_private_subnet.id
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
    Name =  format("%s_general", var.targets_ip)
  }
}

################# instances ####################
# Create EC2 linux instance - targets_ip_pd_pri_a
resource "aws_instance" "targets_ip_pd_pri_a" {
  count = 1
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = format("10.2.101.10%s", count.index)
  subnet_id                   = aws_subnet.targets_ip_private_subnet.id
  vpc_security_group_ids      = [aws_security_group.sg_targets_ip_pd_pri_a.id]
  user_data = file(var.create-web-server)
  tags = {
    Name =  format("targets_ip_pd_pri_a%s",count.index+1)
  }
}


#################### NLB ####################
# Define elastic ip for nlb
resource "aws_eip" "targets_ip_nlb_eip_pd_pri_a" {
  vpc = true
    tags = {
    Name = format("targets_ip_nlb_eip_pd_pri_a")
  }
}
resource "aws_lb" "targets_ip_nlb_pd_pri_a" {
  name = "targets-ip-nlb-pd-pri-a"
  internal           = false
  load_balancer_type = "network"
  subnet_mapping {
  subnet_id     = aws_subnet.targets_ip_public_subnet.id
  allocation_id = aws_eip.targets_ip_nlb_eip_pd_pri_a.id
  }
}
resource "aws_lb_target_group" "targets_ip_nlb_tg_pd_pri_a" {
  name = "targets-ip-nlb-tg-pd-pri-a"
  port     = 80
  protocol = "TCP"
  target_type = "ip"
  vpc_id = aws_vpc.targets_ip.id
}
resource "aws_lb_listener" "targets_ip_nlb_lsnr_pd_pri_a" {
  load_balancer_arn = aws_lb.targets_ip_nlb_pd_pri_a.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.targets_ip_nlb_tg_pd_pri_a.arn
  }
}
resource "aws_lb_target_group_attachment" "targets_ip_nlb_tg_att_pd_pri_a" {
  count = 1
  target_group_arn = aws_lb_target_group.targets_ip_nlb_tg_pd_pri_a.arn
  target_id        = aws_instance.targets_ip_pd_pri_a[count.index].private_ip
  port             = 80
}


#################### VPC Peering ####################
# jump to targets_ip - requester
resource "aws_vpc_peering_connection" "pcx-jump-targets_ip-r" {
  vpc_id        = aws_vpc.jump.id
  peer_vpc_id   = aws_vpc.targets_ip.id
  peer_owner_id = data.aws_caller_identity.requester.account_id
  auto_accept   = true
  tags = {
    Name = "pcx-jump-targets_ip-r"
  }
}



#################### pd_pub_a ####################
# Define security-group
resource "aws_security_group" "sg_targets_ip_pd_pub_a" {
  name = "sg_targets_ip_pd_pub_a"
  vpc_id = aws_vpc.targets_ip.id
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
    Name =  format("%s_general", var.targets_ip)
  }
}

################## instances ####################
# Create EC2 linux instance - targets_ip_pd_pub_a
resource "aws_instance" "targets_ip_pd_pub_a" {
  count = 1
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = format("10.2.101.11%s", count.index)
  subnet_id                   = aws_subnet.targets_ip_private_subnet.id
  vpc_security_group_ids      = [aws_security_group.sg_targets_ip_pd_pub_a.id]
  user_data = file(var.create-web-server)
  tags = {
    Name =  format("targets_ip_pd_pub_a%s",count.index+1)
  }
}

#################### NLB ####################
# Define elastic ip for nlb
resource "aws_eip" "targets_ip_nlb_eip_pd_pub_a" {
  vpc = true
    tags = {
    Name = format("targets_ip_nlb_eip_pd_pub_a")
  }
}
resource "aws_lb" "targets_ip_nlb_pd_pub_a" {
  name = "targets-ip-nlb-pd-pub-a"
  internal           = false
  load_balancer_type = "network"
  subnet_mapping {
  subnet_id     = aws_subnet.targets_ip_public_subnet.id
  allocation_id = aws_eip.targets_ip_nlb_eip_pd_pub_a.id
  }
  tags = {
    Name =  format("targets_ip_nlb_pd_pub_a")
  }
}
resource "aws_lb_target_group" "targets_ip_nlb_tg_pd_pub_a" {
  name = "targets-ip-nlb-tg-pd-pub-a"
  port     = 80
  protocol = "TCP"
  target_type = "ip"
  vpc_id = aws_vpc.targets_ip.id
}
resource "aws_lb_listener" "targets_ip_nlb_lsnr_pd_pub_a" {
  load_balancer_arn = aws_lb.targets_ip_nlb_pd_pub_a.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.targets_ip_nlb_tg_pd_pub_a.arn
  }
}
resource "aws_lb_target_group_attachment" "targets_ip_nlb_tg_att_pd_pub_a" {
  count = 1
  target_group_arn = aws_lb_target_group.targets_ip_nlb_tg_pd_pub_a.arn
  target_id        = aws_instance.targets_ip_pd_pub_a[count.index].private_ip
  port             = 80
}


#################### pe_pri_a ####################
# Define security-group
resource "aws_security_group" "sg_targets_ip_pe_pri_a" {
  name = "sg_targets_ip_pe_pri_a"
  vpc_id = aws_vpc.targets_ip.id
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
      cidr_blocks = ["10.2.1.88/32"]
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
    Name =  format("%s_general", var.targets_ip)
  }
}

################## instances ####################
# Create EC2 linux instance - targets_ip_pe_pri_a
resource "aws_instance" "targets_ip_pe_pri_a" {
  count = 1
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = format("10.2.101.12%s", count.index)
  subnet_id                   = aws_subnet.targets_ip_private_subnet.id
  vpc_security_group_ids      = [aws_security_group.sg_targets_ip_pe_pri_a.id]
  user_data = file(var.create-web-server)
  tags = {
    Name =  format("targets_ip_pe_pri_a%s",count.index+1)
  }
}

#################### NLB ####################
# Define elastic ip for nlb
resource "aws_eip" "targets_ip_nlb_eip_pe_pri_a" {
  vpc = true
    tags = {
    Name = format("targets_ip_nlb_eip_pe_pri_a")
  }
}
resource "aws_lb" "targets_ip_nlb_pe_pri_a" {
  name = "targets-ip-nlb-pe-pri-a"
  internal           = false
  load_balancer_type = "network"
  subnet_mapping {
  subnet_id     = aws_subnet.targets_ip_public_subnet.id
  allocation_id = aws_eip.targets_ip_nlb_eip_pe_pri_a.id
  }
  tags = {
    Name =  format("targets_ip_nlb_pe_pri_a")
  }
}
resource "aws_lb_target_group" "targets_ip_nlb_tg_pe_pri_a" {
  name = "targets-ip-nlb-tg-pe-pri-a"
  port     = 80
  protocol = "TCP"
  target_type = "ip"
  proxy_protocol_v2 = "true"
  vpc_id = aws_vpc.targets_ip.id
  tags = {
    Name =  format("targets_ip_nlb_tg_pe_pri_a")
  }
}
resource "aws_lb_listener" "targets_ip_nlb_lsnr_pe_pri_a" {
  load_balancer_arn = aws_lb.targets_ip_nlb_pe_pri_a.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.targets_ip_nlb_tg_pe_pri_a.arn
  }
}
resource "aws_lb_target_group_attachment" "targets_ip_nlb_tg_att_pe_pri_a" {
  count = 1
  target_group_arn = aws_lb_target_group.targets_ip_nlb_tg_pe_pri_a.arn
  target_id        = aws_instance.targets_ip_pe_pri_a[count.index].private_ip
  port             = 80
}



#################### pe_pub_a ####################
# Define security-group
resource "aws_security_group" "sg_targets_ip_pe_pub_a" {
  name = "sg_targets_ip_pe_pub_a"
  vpc_id = aws_vpc.targets_ip.id
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
    Name =  format("%s_general", var.targets_ip)
  }
}

################## instances ####################
# Create EC2 linux instance - targets_ip_pe_pub_a
resource "aws_instance" "targets_ip_pe_pub_a" {
  count = 1
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = format("10.2.101.13%s", count.index)
  subnet_id                   = aws_subnet.targets_ip_private_subnet.id
  vpc_security_group_ids      = [aws_security_group.sg_targets_ip_pe_pub_a.id]
  user_data = file(var.create-web-server)
  tags = {
    Name =  format("targets_ip_pe_pub_a%s",count.index+1)
  }
}

#################### NLB ####################
# Define elastic ip for nlb
resource "aws_eip" "targets_ip_nlb_eip_pe_pub_a" {
  vpc = true
    tags = {
    Name = format("targets_ip_nlb_eip_pe_pub_a")
  }
}
resource "aws_lb" "targets_ip_nlb_pe_pub_a" {
  name = "targets-ip-nlb-pe-pub-a"
  internal           = false
  load_balancer_type = "network"
  subnet_mapping {
  subnet_id     = aws_subnet.targets_ip_public_subnet.id
  allocation_id = aws_eip.targets_ip_nlb_eip_pe_pub_a.id
  }
  tags = {
    Name =  format("targets_ip_nlb_pe_pub_a")
  }
}
resource "aws_lb_target_group" "targets_ip_nlb_tg_pe_pub_a" {
  name = "targets-ip-nlb-tg-pe-pub-a"
  port     = 80
  protocol = "TCP"
  target_type = "ip"
  proxy_protocol_v2 = "true"
  vpc_id = aws_vpc.targets_ip.id
  tags = {
    Name =  format("targets_ip_nlb_tg_pe_pub_a")
  }
}
resource "aws_lb_listener" "targets_ip_nlb_lsnr_pe_pub_a" {
  load_balancer_arn = aws_lb.targets_ip_nlb_pe_pub_a.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.targets_ip_nlb_tg_pe_pub_a.arn
  }
}
resource "aws_lb_target_group_attachment" "targets_ip_nlb_tg_att_pe_pub_a" {
  count = 1
  target_group_arn = aws_lb_target_group.targets_ip_nlb_tg_pe_pub_a.arn
  target_id        = aws_instance.targets_ip_pe_pub_a[count.index].private_ip
  port             = 80
}





# data "aws_network_interfaces" "this" {
#   filter {
#     name = "description"
#     values = ["ELB net*"]
#   }
#   filter {
#     name = "vpc-id"
#     values = [aws_vpc.targets_ip.id]
#   }
#   filter {
#     name = "status"
#     values = ["in-use"]
#   }
#   filter {
#     name = "attachment.status"
#     values = ["attached"]
#   }
# }

# locals {
#   nlb_interface_ids = flatten([data.aws_network_interfaces.this.ids])
# }

# data "aws_network_interface" "ifs" {
#   count = length(local.nlb_interface_ids)
#   id = local.nlb_interface_ids[count.index]
# }

# output "aws_lb_network_interface_ips" {
#   value = flatten([data.aws_network_interface.ifs.*.private_ips])
# }


# data "aws_lb_network_interface_ips" "ips"{
#   value = flatten([data.aws_network_interface.ifs.*.private_ips])
# }

# locals {
#   count = length()
#   expanded_names = {
#     for name, count in data.aws_lb_network_interface_ips.ips : name => [
#       for i in range(count) : format("%s%02d", name, i)
#     ]
#   }
# }
# output "expanded_names" {
#   value = local.expanded_names
# }
