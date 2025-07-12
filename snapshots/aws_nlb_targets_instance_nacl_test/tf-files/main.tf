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
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx_jump_nlb_target_id_r.id
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





##################################### VPC nlb_target_id ###################################
#################### VPC nlb_target_id vars ####################
# `nlb_target_id` is the vpc keyword being used for tagging in all resources belongs to this vpc.
# replace `nlb_target_id` with your prefered name.

variable "nlb_target_id" {
  description = "VPC Name"
  default     = "nlb_target_id"
}
variable "nlb_target_id_cidr" {
  description = "CIDR block for the VPC"
  default     = "10.2.0.0/16"
}
variable "nlb_target_id_public_subnet_tip_nno" {
  description = "public subnet"
  default     = "10.2.1.0/24"
}
variable "nlb_target_id_private_subnet_tip_nno" {
  description = "same subnet"
  default     = "10.2.101.0/24"
}

#################### vpc ####################
# Define VPC
resource "aws_vpc" "nlb_target_id" {
  cidr_block = var.nlb_target_id_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = var.nlb_target_id
  }
}

############# Subnets #############
# Define public subnet
resource "aws_subnet" "nlb_target_id_public_subnet_tip_nno" {
  vpc_id     = aws_vpc.nlb_target_id.id
  cidr_block = var.nlb_target_id_public_subnet_tip_nno
  map_public_ip_on_launch = "true"
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.nlb_target_id, var.nlb_target_id_public_subnet_tip_nno)
  }
}
# Define nlb_target_id_private_subnet_tip_nno
resource "aws_subnet" "nlb_target_id_private_subnet_tip_nno" {
  vpc_id     = aws_vpc.nlb_target_id.id
  cidr_block = var.nlb_target_id_private_subnet_tip_nno
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.nlb_target_id, var.nlb_target_id_private_subnet_tip_nno)
  }
}

#################### igw-ngw ####################
# Define igw
resource "aws_internet_gateway" "nlb_target_id_igw" {
  vpc_id     = aws_vpc.nlb_target_id.id
  tags = {
    Name = format("nlb_target_id_igw")
  }
}
# Define elastic ip for ngw
resource "aws_eip" "nlb_target_id_ngw_eip" {
  vpc = true
    tags = {
    Name = format("nlb_target_id_ngw_eip")
  }
}
# Define ngw
resource "aws_nat_gateway" "nlb_target_id_ngw" {
  allocation_id = aws_eip.nlb_target_id_ngw_eip.id
  subnet_id     = aws_subnet.nlb_target_id_public_subnet_tip_nno.id
  depends_on = [aws_internet_gateway.nlb_target_id_igw]
    tags = {
    Name = format("nlb_target_id_ngw")
  }
}

#################### route tables ####################
# Define route table - igw
resource "aws_route_table" "nlb_target_id_rtb_igw" {
  vpc_id = aws_vpc.nlb_target_id.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.nlb_target_id_igw.id
  }
  tags = {
    Name = format("%s_rtb_igw", var.nlb_target_id)
  }
}
# associate route table to nlb_target_id_public_subnet_tip_nno
resource "aws_route_table_association" "nlb_target_id_rtb_asctn_nlb_target_id_public_subnet_tip_nno" {
  route_table_id = aws_route_table.nlb_target_id_rtb_igw.id
  subnet_id      = aws_subnet.nlb_target_id_public_subnet_tip_nno.id
}

# Define route table  - ngw
resource "aws_route_table" "nlb_target_id_rtb_ngw" {
  vpc_id = aws_vpc.nlb_target_id.id
  route {
    cidr_block = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nlb_target_id_ngw.id
  }
  route {
    cidr_block = "10.1.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx_jump_nlb_target_id_r.id
  }
}
# associate route table to nlb_target_id_private_subnet_tip_nno
resource "aws_route_table_association" "nlb_target_id_rtb_asctn_nlb_target_id_private_subnet_tip_nno" {
  route_table_id = aws_route_table.nlb_target_id_rtb_ngw.id
  subnet_id      = aws_subnet.nlb_target_id_private_subnet_tip_nno.id
}

############# security-group #############
# Define security-group
resource "aws_security_group" "nlb_target_id_general_sg" {
  name = "nlb_target_id_general_sg"
  vpc_id = aws_vpc.nlb_target_id.id
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
      cidr_blocks = ["0.0.0.0/0"]
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
    Name =  format("%s_pri_pub_a", var.nlb_target_id)
  }
}
############# NACL #############
resource "aws_network_acl" "nlb_target_id_nlb_nacl_tip_nno" {
  vpc_id = aws_vpc.nlb_target_id.id
  subnet_ids = [
    aws_subnet.nlb_target_id_public_subnet_tip_nno.id
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
    protocol   = "tcp"
    rule_no    = 10
    action     = "deny"
    cidr_block = "10.2.101.100/32"
    from_port  = 80
    to_port    = 80
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
    Name =  format("nlb_target_id_nlb_nacl_tip_nno")
  }
}
resource "aws_network_acl" "nlb_target_id_target_nacl_tip_nno" {
  vpc_id = aws_vpc.nlb_target_id.id
  subnet_ids = [
    aws_subnet.nlb_target_id_private_subnet_tip_nno.id
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
    Name =  format("nlb_target_id_target_nacl_tip_nno")
  }
}

################# instances ####################
# Create EC2 linux instance - nlb_target_id_web_tip_nno
resource "aws_instance" "nlb_target_id_web_tip_nno" {
  count = 1
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = format("10.2.101.10%s", count.index)
  subnet_id                   = aws_subnet.nlb_target_id_private_subnet_tip_nno.id
  vpc_security_group_ids      = [aws_security_group.nlb_target_id_general_sg.id]
  user_data = file(var.create-web-server)
  tags = {
    Name =  format("nlb_target_id_web_tip_nno%s",count.index+1)
  }
}


#################### NLB ####################
resource "aws_lb" "nlb_target_id_nlb_tip_nno" {
  name = "nlb-target-id-nlb-tip-nno"
  internal           = false
  load_balancer_type = "network"
  subnet_mapping {
  subnet_id     = aws_subnet.nlb_target_id_public_subnet_tip_nno.id
  }
}
resource "aws_lb_target_group" "nlb_target_id_nlb_tip_nno_tg" {
  name = "nlb-target-id-nlb-tip-nno-tg"
  port     = 80
  protocol = "TCP"
  vpc_id = aws_vpc.nlb_target_id.id
}
resource "aws_lb_listener" "nlb_target_id_nlb_tip_nno_lsnr" {
  load_balancer_arn = aws_lb.nlb_target_id_nlb_tip_nno.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.nlb_target_id_nlb_tip_nno_tg.arn
  }
}
resource "aws_lb_target_group_attachment" "nlb_target_id_nlb_tip_nno_tg_att" {
  count = 1
  target_group_arn = aws_lb_target_group.nlb_target_id_nlb_tip_nno_tg.arn
  target_id        = aws_instance.nlb_target_id_web_tip_nno[count.index].id
  port             = 80
}








##################################### NLB  - cip_tni ###################################
variable "nlb_target_id_public_subnet_cip_tni" {
  description = "public subnet"
  default     = "10.2.2.0/24"
}
variable "nlb_target_id_private_subnet_cip_tni" {
  description = "same subnet"
  default     = "10.2.102.0/24"
}
############# Subnets #############
# Define public subnet
resource "aws_subnet" "nlb_target_id_public_subnet_cip_tni" {
  vpc_id     = aws_vpc.nlb_target_id.id
  cidr_block = var.nlb_target_id_public_subnet_cip_tni
  map_public_ip_on_launch = "true"
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.nlb_target_id, var.nlb_target_id_public_subnet_cip_tni)
  }
}
# Define nlb_target_id_private_subnet_cip_tni
resource "aws_subnet" "nlb_target_id_private_subnet_cip_tni" {
  vpc_id     = aws_vpc.nlb_target_id.id
  cidr_block = var.nlb_target_id_private_subnet_cip_tni
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.nlb_target_id, var.nlb_target_id_private_subnet_cip_tni)
  }
}
# associate route table to nlb_target_id_public_subnet_cip_tni
resource "aws_route_table_association" "nlb_target_id_rtb_asctn_nlb_target_id_public_subnet_cip_tni" {
  route_table_id = aws_route_table.nlb_target_id_rtb_igw.id
  subnet_id      = aws_subnet.nlb_target_id_public_subnet_cip_tni.id
}
# associate route table to nlb_target_id_private_subnet_cip_tni
resource "aws_route_table_association" "nlb_target_id_rtb_asctn_nlb_target_id_private_subnet_cip_tni" {
  route_table_id = aws_route_table.nlb_target_id_rtb_ngw.id
  subnet_id      = aws_subnet.nlb_target_id_private_subnet_cip_tni.id
}
############# NACL #############
resource "aws_network_acl" "nlb_target_id_nlb_nacl_cip_tni" {
  vpc_id = aws_vpc.nlb_target_id.id
  subnet_ids = [
    aws_subnet.nlb_target_id_public_subnet_cip_tni.id
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
    Name =  format("nlb_target_id_nlb_nacl_cip_tni")
  }
}
resource "aws_network_acl" "nlb_target_id_target_nacl_cip_tni" {
  vpc_id = aws_vpc.nlb_target_id.id
  subnet_ids = [
    aws_subnet.nlb_target_id_private_subnet_cip_tni.id
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
    protocol   = "tcp"
    rule_no    = 30
    action     = "deny"
    cidr_block = "8.8.8.8/32"
    from_port  = 80
    to_port    = 80
  }
  ingress {
    protocol   = "tcp"
    rule_no    = 40
    action     = "deny"
    cidr_block = "67.160.71.197/32"
    from_port  = 80
    to_port    = 80
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
    Name =  format("nlb_target_id_target_nacl_cip_tni")
  }
}

################# instances ####################
# Create EC2 linux instance - nlb_target_id_web_cip_tni
resource "aws_instance" "nlb_target_id_web_cip_tni" {
  count = 1
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = format("10.2.102.10%s", count.index)
  subnet_id                   = aws_subnet.nlb_target_id_private_subnet_cip_tni.id
  vpc_security_group_ids      = [aws_security_group.nlb_target_id_general_sg.id]
  user_data = file(var.create-web-server)
  tags = {
    Name =  format("nlb_target_id_web_cip_tni%s",count.index+1)
  }
}
#################### NLB ####################
resource "aws_lb" "nlb_target_id_nlb_cip_tni" {
  name = "nlb-target-id-nlb-cip-tni"
  internal           = false
  load_balancer_type = "network"
  subnet_mapping {
  subnet_id     = aws_subnet.nlb_target_id_public_subnet_cip_tni.id
  }
}
resource "aws_lb_target_group" "nlb_target_id_nlb_cip_tni_tg" {
  name = "nlb-target-id-nlb-cip-tni-tg"
  port     = 80
  protocol = "TCP"
  vpc_id = aws_vpc.nlb_target_id.id
}
resource "aws_lb_listener" "nlb_target_id_nlb_cip_tni_lsnr" {
  load_balancer_arn = aws_lb.nlb_target_id_nlb_cip_tni.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.nlb_target_id_nlb_cip_tni_tg.arn
  }
}
resource "aws_lb_target_group_attachment" "nlb_target_id_nlb_cip_tni_tg_att" {
  count = 1
  target_group_arn = aws_lb_target_group.nlb_target_id_nlb_cip_tni_tg.arn
  target_id        = aws_instance.nlb_target_id_web_cip_tni[count.index].id
  port             = 80
}




##################################### NLB  - cip_tno ###################################
variable "nlb_target_id_public_subnet_cip_tno" {
  description = "public subnet"
  default     = "10.2.3.0/24"
}
variable "nlb_target_id_private_subnet_cip_tno" {
  description = "same subnet"
  default     = "10.2.103.0/24"
}
############# Subnets #############
# Define public subnet
resource "aws_subnet" "nlb_target_id_public_subnet_cip_tno" {
  vpc_id     = aws_vpc.nlb_target_id.id
  cidr_block = var.nlb_target_id_public_subnet_cip_tno
  map_public_ip_on_launch = "true"
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.nlb_target_id, var.nlb_target_id_public_subnet_cip_tno)
  }
}
# Define nlb_target_id_private_subnet_cip_tno
resource "aws_subnet" "nlb_target_id_private_subnet_cip_tno" {
  vpc_id     = aws_vpc.nlb_target_id.id
  cidr_block = var.nlb_target_id_private_subnet_cip_tno
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.nlb_target_id, var.nlb_target_id_private_subnet_cip_tno)
  }
}
# associate route table to nlb_target_id_public_subnet_cip_tno
resource "aws_route_table_association" "nlb_target_id_rtb_asctn_nlb_target_id_public_subnet_cip_tno" {
  route_table_id = aws_route_table.nlb_target_id_rtb_igw.id
  subnet_id      = aws_subnet.nlb_target_id_public_subnet_cip_tno.id
}
# associate route table to nlb_target_id_private_subnet_cip_tno
resource "aws_route_table_association" "nlb_target_id_rtb_asctn_nlb_target_id_private_subnet_cip_tno" {
  route_table_id = aws_route_table.nlb_target_id_rtb_ngw.id
  subnet_id      = aws_subnet.nlb_target_id_private_subnet_cip_tno.id
}
############# NACL #############
resource "aws_network_acl" "nlb_target_id_nlb_nacl_cip_tno" {
  vpc_id = aws_vpc.nlb_target_id.id
  subnet_ids = [
    aws_subnet.nlb_target_id_public_subnet_cip_tno.id
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
    Name =  format("nlb_target_id_nlb_nacl_cip_tno")
  }
}
resource "aws_network_acl" "nlb_target_id_target_nacl_cip_tno" {
  vpc_id = aws_vpc.nlb_target_id.id
  subnet_ids = [
    aws_subnet.nlb_target_id_private_subnet_cip_tno.id
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
    protocol   = "tcp"
    rule_no    = 30
    action     = "deny"
    cidr_block = "8.8.8.8/32"
    from_port  = 1024
    to_port    = 65535
  }
  egress {
    protocol   = "tcp"
    rule_no    = 40
    action     = "deny"
    cidr_block = "67.160.71.197/32"
    from_port  = 1024
    to_port    = 65535
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
    Name =  format("nlb_target_id_target_nacl_cip_tno")
  }
}

################# instances ####################
# Create EC2 linux instance - nlb_target_id_web_cip_tno
resource "aws_instance" "nlb_target_id_web_cip_tno" {
  count = 1
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = format("10.2.103.10%s", count.index)
  subnet_id                   = aws_subnet.nlb_target_id_private_subnet_cip_tno.id
  vpc_security_group_ids      = [aws_security_group.nlb_target_id_general_sg.id]
  user_data = file(var.create-web-server)
  tags = {
    Name =  format("nlb_target_id_web_cip_tno%s",count.index+1)
  }
}
#################### NLB ####################
resource "aws_lb" "nlb_target_id_nlb_cip_tno" {
  name = "nlb-target-id-nlb-cip-tno"
  internal           = false
  load_balancer_type = "network"
  subnet_mapping {
  subnet_id     = aws_subnet.nlb_target_id_public_subnet_cip_tno.id
  }
}
resource "aws_lb_target_group" "nlb_target_id_nlb_cip_tno_tg" {
  name = "nlb-target-id-nlb-cip-tno-tg"
  port     = 80
  protocol = "TCP"
  vpc_id = aws_vpc.nlb_target_id.id
}
resource "aws_lb_listener" "nlb_target_id_nlb_cip_tno_lsnr" {
  load_balancer_arn = aws_lb.nlb_target_id_nlb_cip_tno.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.nlb_target_id_nlb_cip_tno_tg.arn
  }
}
resource "aws_lb_target_group_attachment" "nlb_target_id_nlb_cip_tno_tg_att" {
  count = 1
  target_group_arn = aws_lb_target_group.nlb_target_id_nlb_cip_tno_tg.arn
  target_id        = aws_instance.nlb_target_id_web_cip_tno[count.index].id
  port             = 80
}





##################################### NLB  - tip_nni ###################################
variable "nlb_target_id_public_subnet_tip_nni" {
  description = "public subnet"
  default     = "10.2.4.0/24"
}
variable "nlb_target_id_private_subnet_tip_nni" {
  description = "same subnet"
  default     = "10.2.104.0/24"
}
############# Subnets #############
# Define public subnet
resource "aws_subnet" "nlb_target_id_public_subnet_tip_nni" {
  vpc_id     = aws_vpc.nlb_target_id.id
  cidr_block = var.nlb_target_id_public_subnet_tip_nni
  map_public_ip_on_launch = "true"
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.nlb_target_id, var.nlb_target_id_public_subnet_tip_nni)
  }
}
# Define nlb_target_id_private_subnet_tip_nni
resource "aws_subnet" "nlb_target_id_private_subnet_tip_nni" {
  vpc_id     = aws_vpc.nlb_target_id.id
  cidr_block = var.nlb_target_id_private_subnet_tip_nni
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.nlb_target_id, var.nlb_target_id_private_subnet_tip_nni)
  }
}
# associate route table to nlb_target_id_public_subnet_tip_nni
resource "aws_route_table_association" "nlb_target_id_rtb_asctn_nlb_target_id_public_subnet_tip_nni" {
  route_table_id = aws_route_table.nlb_target_id_rtb_igw.id
  subnet_id      = aws_subnet.nlb_target_id_public_subnet_tip_nni.id
}
# associate route table to nlb_target_id_private_subnet_tip_nni
resource "aws_route_table_association" "nlb_target_id_rtb_asctn_nlb_target_id_private_subnet_tip_nni" {
  route_table_id = aws_route_table.nlb_target_id_rtb_ngw.id
  subnet_id      = aws_subnet.nlb_target_id_private_subnet_tip_nni.id
}
############# NACL #############
resource "aws_network_acl" "nlb_target_id_nlb_nacl_tip_nni" {
  vpc_id = aws_vpc.nlb_target_id.id
  subnet_ids = [
    aws_subnet.nlb_target_id_public_subnet_tip_nni.id
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
    protocol   = "tcp"
    rule_no    = 30
    action     = "deny"
    cidr_block = "10.2.104.100/32"
    from_port  = 1024
    to_port    = 65535
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
    Name =  format("nlb_target_id_nlb_nacl_tip_nni")
  }
}
resource "aws_network_acl" "nlb_target_id_target_nacl_tip_nni" {
  vpc_id = aws_vpc.nlb_target_id.id
  subnet_ids = [
    aws_subnet.nlb_target_id_private_subnet_tip_nni.id
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
    Name =  format("nlb_target_id_target_nacl_tip_nni")
  }
}

################# instances ####################
# Create EC2 linux instance - nlb_target_id_web_tip_nni
resource "aws_instance" "nlb_target_id_web_tip_nni" {
  count = 1
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = format("10.2.104.10%s", count.index)
  subnet_id                   = aws_subnet.nlb_target_id_private_subnet_tip_nni.id
  vpc_security_group_ids      = [aws_security_group.nlb_target_id_general_sg.id]
  user_data = file(var.create-web-server)
  tags = {
    Name =  format("nlb_target_id_web_tip_nni%s",count.index+1)
  }
}
#################### NLB ####################
resource "aws_lb" "nlb_target_id_nlb_tip_nni" {
  name = "nlb-target-id-nlb-tip-nni"
  internal           = false
  load_balancer_type = "network"
  subnet_mapping {
  subnet_id     = aws_subnet.nlb_target_id_public_subnet_tip_nni.id
  }
}
resource "aws_lb_target_group" "nlb_target_id_nlb_tip_nni_tg" {
  name = "nlb-target-id-nlb-tip-nni-tg"
  port     = 80
  protocol = "TCP"
  vpc_id = aws_vpc.nlb_target_id.id
}
resource "aws_lb_listener" "nlb_target_id_nlb_tip_nni_lsnr" {
  load_balancer_arn = aws_lb.nlb_target_id_nlb_tip_nni.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.nlb_target_id_nlb_tip_nni_tg.arn
  }
}
resource "aws_lb_target_group_attachment" "nlb_target_id_nlb_tip_nni_tg_att" {
  count = 1
  target_group_arn = aws_lb_target_group.nlb_target_id_nlb_tip_nni_tg.arn
  target_id        = aws_instance.nlb_target_id_web_tip_nni[count.index].id
  port             = 80
}





##################################### NLB  - nip_tni ###################################
variable "nlb_target_id_public_subnet_nip_tni" {
  description = "public subnet"
  default     = "10.2.5.0/24"
}
variable "nlb_target_id_private_subnet_nip_tni" {
  description = "same subnet"
  default     = "10.2.105.0/24"
}
############# Subnets #############
# Define public subnet
resource "aws_subnet" "nlb_target_id_public_subnet_nip_tni" {
  vpc_id     = aws_vpc.nlb_target_id.id
  cidr_block = var.nlb_target_id_public_subnet_nip_tni
  map_public_ip_on_launch = "true"
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.nlb_target_id, var.nlb_target_id_public_subnet_nip_tni)
  }
}
# Define nlb_target_id_private_subnet_nip_tni
resource "aws_subnet" "nlb_target_id_private_subnet_nip_tni" {
  vpc_id     = aws_vpc.nlb_target_id.id
  cidr_block = var.nlb_target_id_private_subnet_nip_tni
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = {
    Name = format("%s_%s", var.nlb_target_id, var.nlb_target_id_private_subnet_nip_tni)
  }
}
# associate route table to nlb_target_id_public_subnet_nip_tni
resource "aws_route_table_association" "nlb_target_id_rtb_asctn_nlb_target_id_public_subnet_nip_tni" {
  route_table_id = aws_route_table.nlb_target_id_rtb_igw.id
  subnet_id      = aws_subnet.nlb_target_id_public_subnet_nip_tni.id
}
# associate route table to nlb_target_id_private_subnet_nip_tni
resource "aws_route_table_association" "nlb_target_id_rtb_asctn_nlb_target_id_private_subnet_nip_tni" {
  route_table_id = aws_route_table.nlb_target_id_rtb_ngw.id
  subnet_id      = aws_subnet.nlb_target_id_private_subnet_nip_tni.id
}
############# NACL #############
resource "aws_network_acl" "nlb_target_id_nlb_nacl_nip_tni" {
  vpc_id = aws_vpc.nlb_target_id.id
  subnet_ids = [
    aws_subnet.nlb_target_id_public_subnet_nip_tni.id
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
    Name =  format("nlb_target_id_nlb_nacl_nip_tni")
  }
}
resource "aws_network_acl" "nlb_target_id_target_nacl_nip_tni" {
  vpc_id = aws_vpc.nlb_target_id.id
  subnet_ids = [
    aws_subnet.nlb_target_id_private_subnet_nip_tni.id
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
  ingress {
    protocol   = "tcp"
    rule_no    = 30
    action     = "deny"
    cidr_block = "10.2.5.156/32"
    from_port  = 80
    to_port    = 80
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
    Name =  format("nlb_target_id_target_nacl_nip_tni")
  }
}

################# instances ####################
# Create EC2 linux instance - nlb_target_id_web_nip_tni
resource "aws_instance" "nlb_target_id_web_nip_tni" {
  count = 1
  ami                         = var.instance_ami_a41
  instance_type               = var.instance_type_t2_micro
  key_name                    = aws_key_pair.ec2key.key_name
  private_ip                  = format("10.2.105.10%s", count.index)
  subnet_id                   = aws_subnet.nlb_target_id_private_subnet_nip_tni.id
  vpc_security_group_ids      = [aws_security_group.nlb_target_id_general_sg.id]
  user_data = file(var.create-web-server)
  tags = {
    Name =  format("nlb_target_id_web_nip_tni%s",count.index+1)
  }
}
#################### NLB ####################
resource "aws_lb" "nlb_target_id_nlb_nip_tni" {
  name = "nlb-target-id-nlb-nip-tni"
  internal           = false
  load_balancer_type = "network"
  subnet_mapping {
  subnet_id     = aws_subnet.nlb_target_id_public_subnet_nip_tni.id
  }
}
resource "aws_lb_target_group" "nlb_target_id_nlb_nip_tni_tg" {
  name = "nlb-target-id-nlb-nip-tni-tg"
  port     = 80
  protocol = "TCP"
  vpc_id = aws_vpc.nlb_target_id.id
}
resource "aws_lb_listener" "nlb_target_id_nlb_nip_tni_lsnr" {
  load_balancer_arn = aws_lb.nlb_target_id_nlb_nip_tni.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.nlb_target_id_nlb_nip_tni_tg.arn
  }
}
resource "aws_lb_target_group_attachment" "nlb_target_id_nlb_nip_tni_tg_att" {
  count = 1
  target_group_arn = aws_lb_target_group.nlb_target_id_nlb_nip_tni_tg.arn
  target_id        = aws_instance.nlb_target_id_web_nip_tni[count.index].id
  port             = 80
}


#################### VPC Peering ####################
# jump to nlb_target_id - requester
resource "aws_vpc_peering_connection" "pcx_jump_nlb_target_id_r" {
  vpc_id        = aws_vpc.jump.id
  peer_vpc_id   = aws_vpc.nlb_target_id.id
  peer_owner_id = data.aws_caller_identity.requester.account_id
  auto_accept   = true
  tags = {
    Name = "pcx_jump_nlb_target_id_r"
  }
}
