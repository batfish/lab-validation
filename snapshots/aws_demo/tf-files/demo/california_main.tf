#################### Provider ####################
provider "aws" {
  profile = var.profile
  alias = "provider-2"
  region  = var.region-2
}
# Use existing ssh key pair
resource "aws_key_pair" "provider-2-ec2key" {
  provider = aws.provider-2
  key_name = "publicKey"
  public_key = file(var.public-key-path)
}
# Declare the AZ data source
data "aws_availability_zones" "az-provider-2" {
  provider = aws.provider-2
  state = "available"
}
######################################## vpc-hr-west ########################################
#################### vpc ####################
# Define VPC
resource "aws_vpc" "vpc-hr-west" {
  provider = aws.provider-2
  cidr_block = var.cidr-hr-west
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = var.vpc-hr-west
  }
}

#################### subnet ####################
# Define public subnet
resource "aws_subnet" "subnet-public-hr-west" {
  provider = aws.provider-2
  vpc_id     = aws_vpc.vpc-hr-west.id
  cidr_block = var.subnet-public-hr-west
  availability_zone = data.aws_availability_zones.az-provider-2.names[0]
  tags = {
    Name = format("subnet-public-hr-west")
  }
}
# Define web subnet
resource "aws_subnet" "subnet-web-hr-west" {
  provider = aws.provider-2
  vpc_id     = aws_vpc.vpc-hr-west.id
  cidr_block = var.subnet-web-hr-west
  availability_zone = data.aws_availability_zones.az-provider-2.names[0]
  tags = {
    Name = format("subnet-web-hr-west")
  }
}
# Define data subnet
resource "aws_subnet" "subnet-data-hr-west" {
  provider = aws.provider-2
  vpc_id     = aws_vpc.vpc-hr-west.id
  cidr_block = var.subnet-data-hr-west
  availability_zone = data.aws_availability_zones.az-provider-2.names[0]
  tags = {
    Name = format("subnet-data-hr-west")
  }
}
# Define tgw subnet
resource "aws_subnet" "subnet-tgw-hr-west" {
  provider = aws.provider-2
  vpc_id     = aws_vpc.vpc-hr-west.id
  cidr_block = var.subnet-tgw-hr-west
  availability_zone = data.aws_availability_zones.az-provider-2.names[0]
  tags = {
    Name = format("subnet-tgw-hr-west")
  }
}

#################### igw-ngw ####################
# Define igw
resource "aws_internet_gateway" "igw-hr-west" {
  provider = aws.provider-2
  vpc_id = aws_vpc.vpc-hr-west.id
  tags = {
    Name = format("igw-hr-west")
  }
}
# Define elastic ip for ngw
resource "aws_eip" "eip-ngw-hr-west" {
  provider = aws.provider-2
  vpc = true
    tags = {
    Name = format("eip-ngw-hr-west")
  }
}
# Define ngw
resource "aws_nat_gateway" "ngw-hr-west" {
  provider = aws.provider-2
  allocation_id = aws_eip.eip-ngw-hr-west.id
  subnet_id     = aws_subnet.subnet-public-hr-west.id
  depends_on = [aws_internet_gateway.igw-hr-west]
    tags = {
    Name = format("ngw-hr-west")
  }
}

#################### route tables ####################
# Define route table  - igw
resource "aws_route_table" "rtb-igw-hr-west" {
  provider = aws.provider-2
  vpc_id = aws_vpc.vpc-hr-west.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw-hr-west.id
  }
  route {
    cidr_block = "10.4.0.0/16"
    transit_gateway_id = aws_ec2_transit_gateway.tgw-west.id
  }
  route {
    cidr_block = "10.1.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-hr-west-east-r.id
  }
  tags = {
    Name = format("rtb-igw-hr-west")
  }
}
# associate igw route table to the public subnet
resource "aws_route_table_association" "rtb-asctn-igw-public-hr-west" {
  provider = aws.provider-2
  route_table_id = aws_route_table.rtb-igw-hr-west.id
  subnet_id      = aws_subnet.subnet-public-hr-west.id
}

# Define route table  - ngw
resource "aws_route_table" "rtb-ngw-hr-west" {
  provider = aws.provider-2
  vpc_id = aws_vpc.vpc-hr-west.id
  route {
    cidr_block = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.ngw-hr-west.id
  }
  route {
    cidr_block = "10.4.0.0/16"
    transit_gateway_id = aws_ec2_transit_gateway.tgw-west.id
  }
  route {
    cidr_block = "10.1.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-hr-west-east-r.id
  }
  tags = {
    Name = format("rtb-ngw-hr-west")
  }
}
# associate ngw route table to the db subnet
resource "aws_route_table_association" "rtb-asctn-ngw-data-hr-west" {
  provider = aws.provider-2
  route_table_id = aws_route_table.rtb-ngw-hr-west.id
  subnet_id      = aws_subnet.subnet-data-hr-west.id
}
# associate ngw route table to the web subnet
resource "aws_route_table_association" "rtb-asctn-ngw-web-hr-west" {
  provider = aws.provider-2
  route_table_id = aws_route_table.rtb-ngw-hr-west.id
  subnet_id      = aws_subnet.subnet-web-hr-west.id
}
# associate ngw route table to the tgw subnet
resource "aws_route_table_association" "rtb-asctn-ngw-tgw-hr-west" {
  provider = aws.provider-2
  route_table_id = aws_route_table.rtb-ngw-hr-west.id
  subnet_id      = aws_subnet.subnet-tgw-hr-west.id
}

############# SG #############
# Define security-group web
resource "aws_security_group" "sg-web-hr-west" {
  provider = aws.provider-2
  vpc_id = aws_vpc.vpc-hr-west.id
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
      cidr_blocks = ["10.0.0.0/8", "172.16.0.0/20", "192.168.0.0/16"]
      description = "ICMP Access"
  }
  ingress {
      from_port   = 33434
      to_port     = 33534
      protocol    = "udp"
      cidr_blocks = ["10.0.0.0/8", "172.16.0.0/20", "192.168.0.0/16"]
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
    Name = format("sg-web-hr-west")
  }
}
# Define security-group db
resource "aws_security_group" "sg-db-hr-west" {
  provider = aws.provider-2
  vpc_id = aws_vpc.vpc-hr-west.id
  # SSH access is controlled at NACL
  ingress {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "SSH Access"
  }
  ingress {
      from_port   = 3306
      to_port     = 3306
      protocol    = "tcp"
      cidr_blocks = ["10.0.0.0/8", "172.16.0.0/20", "192.168.0.0/16"]
      description = "MYSQL Access"
  }
  ingress {
      from_port   = 8
      to_port     = 0
      protocol    = "icmp"
      cidr_blocks = ["10.0.0.0/8", "172.16.0.0/20", "192.168.0.0/16"]
      description = "ICMP Access"
  }
  ingress {
      from_port   = 33434
      to_port     = 33534
      protocol    = "udp"
      cidr_blocks = ["10.0.0.0/8", "172.16.0.0/20", "192.168.0.0/16"]
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
    Name = format("sg-db-hr-west")
  }
}

# Define security-group files
resource "aws_security_group" "sg-file-hr-west" {
  provider = aws.provider-2
  vpc_id = aws_vpc.vpc-hr-west.id
  # SSH access is controlled at NACL
  ingress {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "SSH Access"
  }
  ingress {
      from_port   = 445
      to_port     = 445
      protocol    = "tcp"
      cidr_blocks = ["10.0.0.0/8", "172.16.0.0/20", "192.168.0.0/16"]
      description = "SMB Access"
  }
  ingress {
      from_port   = 8
      to_port     = 0
      protocol    = "icmp"
      cidr_blocks = ["10.0.0.0/8", "172.16.0.0/20", "192.168.0.0/16"]
      description = "ICMP Access"
  }
  ingress {
      from_port   = 33434
      to_port     = 33534
      protocol    = "udp"
      cidr_blocks = ["10.0.0.0/8", "172.16.0.0/20", "192.168.0.0/16"]
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
    Name = format("sg-file-hr-west")
  }
}

############# NACL #############
resource "aws_network_acl" "nacl-hr-west" {
  provider = aws.provider-2
  vpc_id = aws_vpc.vpc-hr-west.id
  subnet_ids = [
    aws_subnet.subnet-web-hr-west.id,
    aws_subnet.subnet-data-hr-west.id
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
    Name = format("nacl-hr-west")
  }
}

resource "aws_network_acl" "nacl-tgw-hr-west" {
  provider = aws.provider-2
  vpc_id = aws_vpc.vpc-hr-west.id
  subnet_ids = [
    aws_subnet.subnet-tgw-hr-west.id
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
    Name = format("nacl-tgw-hr-west")
  }
}


#################### instances ####################
# Create EC2 linux instance - web
resource "aws_instance" "web-vpc-hr-west" {
  provider = aws.provider-2
  count = 2
  ami = var.california-ec2-instance-ami
  instance_type = var.california-ec2-instance-type
  key_name = aws_key_pair.provider-2-ec2key.key_name
  subnet_id = aws_subnet.subnet-web-hr-west.id
  vpc_security_group_ids = [aws_security_group.sg-web-hr-west.id]
  depends_on = [aws_internet_gateway.igw-hr-west]
  user_data = file(var.create-web-server)
  tags = {
    Name =  format("web%s-hr-west", count.index+1)
  }
}
# Create EC2 linux instance - db
resource "aws_instance" "db-vpc-hr-west" {
  provider = aws.provider-2
  count = 1
  ami = var.california-ec2-instance-ami
  instance_type = var.california-ec2-instance-type
  key_name = aws_key_pair.provider-2-ec2key.key_name
  subnet_id = aws_subnet.subnet-data-hr-west.id
  vpc_security_group_ids = [aws_security_group.sg-db-hr-west.id]
  depends_on = [aws_nat_gateway.ngw-hr-west]
  user_data = file(var.update-server)
  tags = {
    Name =  format("db%s-hr-west", count.index+1)
  }
}
# Create EC2 linux instance - file server
resource "aws_instance" "file-vpc-hr-west" {
  provider = aws.provider-2
  count = 1
  ami = var.california-ec2-instance-ami
  instance_type = var.california-ec2-instance-type
  key_name = aws_key_pair.provider-2-ec2key.key_name
  subnet_id = aws_subnet.subnet-data-hr-west.id
  vpc_security_group_ids = [aws_security_group.sg-file-hr-west.id]
  depends_on = [aws_nat_gateway.ngw-hr-west]
  user_data = file(var.update-server)
  tags = {
    Name =  format("file%s-hr-west", count.index+1)
  }
}

#################### NLB ####################
# Define elastic ip for nlb
resource "aws_eip" "eip-nlb-hr-west" {
  provider = aws.provider-2
  vpc = true
    tags = {
    Name = format("eip-nlb-hr-west")
  }
}
resource "aws_lb" "nlb-web-hr-west" {
  name = "nlb-web-hr-west"
  provider = aws.provider-2
  internal           = false
  load_balancer_type = "network"
  subnet_mapping {
  subnet_id     = aws_subnet.subnet-public-hr-west.id
  allocation_id = aws_eip.eip-nlb-hr-west.id
}
  tags = {
    Name =  format("nlb-web-hr-west")
  }
}

resource "aws_lb_target_group" "nlb-web-http-tg-hr-west" {
  provider = aws.provider-2
  port     = 80
  protocol = "TCP"
  vpc_id   = aws_vpc.vpc-hr-west.id
  stickiness {
    enabled = false
    type = "lb_cookie"
  }
}
resource "aws_lb_listener" "nlb-web-http-lsntr-hr-west" {
  provider = aws.provider-2
  load_balancer_arn = aws_lb.nlb-web-hr-west.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.nlb-web-http-tg-hr-west.arn
  }
}
resource "aws_lb_target_group_attachment" "nlb-web-http-tg-atchmnt-hr-west" {
  count = 2
  provider = aws.provider-2
  target_group_arn = aws_lb_target_group.nlb-web-http-tg-hr-west.arn
  target_id        = aws_instance.web-vpc-hr-west[count.index].id
  port             = 80
}

resource "aws_lb_target_group" "nlb-web-https-tg-hr-west" {
  provider = aws.provider-2
  port     = 443
  protocol = "TCP"
  vpc_id   = aws_vpc.vpc-hr-west.id
  stickiness {
    enabled = false
    type = "lb_cookie"
  }
}
resource "aws_lb_listener" "nlb-web-https-lsntr-hr-west" {
  provider = aws.provider-2
  load_balancer_arn = aws_lb.nlb-web-hr-west.arn
  port              = 443
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.nlb-web-https-tg-hr-west.arn
  }
}
resource "aws_lb_target_group_attachment" "nlb-web-https-tg-atchmnt-hr-west" {
  count = 2
  provider = aws.provider-2
  target_group_arn = aws_lb_target_group.nlb-web-https-tg-hr-west.arn
  target_id        = aws_instance.web-vpc-hr-west[count.index].id
  port             = 443
}


######################################## vpc-it-west ########################################
#################### vpc ####################
# Define VPC
resource "aws_vpc" "vpc-it-west" {
  provider = aws.provider-2
  cidr_block = var.cidr-it-west
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = var.vpc-it-west
  }
}

#################### subnet ####################
# Define jump subnet
resource "aws_subnet" "subnet-jump-it-west" {
  provider = aws.provider-2
  vpc_id     = aws_vpc.vpc-it-west.id
  cidr_block = var.subnet-jump-it-west
  map_public_ip_on_launch = "true"
  availability_zone = data.aws_availability_zones.az-provider-2.names[0]
  tags = {
    Name = format("subnet-jump-it-west")
  }
}
# Define tgw subnet
resource "aws_subnet" "subnet-tgw-it-west" {
  provider = aws.provider-2
  vpc_id     = aws_vpc.vpc-it-west.id
  cidr_block = var.subnet-tgw-it-west
  availability_zone = data.aws_availability_zones.az-provider-2.names[0]
  tags = {
    Name = format("subnet-tgw-it-west")
  }
}
#################### igw-ngw ####################
# Define igw
resource "aws_internet_gateway" "igw-it-west" {
  provider = aws.provider-2
  vpc_id = aws_vpc.vpc-it-west.id
  tags = {
    Name = format("igw-it-west")
  }
}

#################### route tables ####################
# Define route table  - igw
resource "aws_route_table" "rtb-igw-it-west" {
  provider = aws.provider-2
  vpc_id = aws_vpc.vpc-it-west.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw-it-west.id
  }
  route {
    cidr_block = "10.3.0.0/16"
    transit_gateway_id = aws_ec2_transit_gateway.tgw-west.id
  }
  route {
    cidr_block = "10.1.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-it-west-hr-east-r.id
  }
  route {
    cidr_block = "10.2.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-it-west-fin-east-r.id
  }
  tags = {
    Name = format("rtb-igw-it-west")
  }
}
# associate igw route table to the jump subnet
resource "aws_route_table_association" "rtb-asctn-igw-jump-it-west" {
  provider = aws.provider-2
  route_table_id = aws_route_table.rtb-igw-it-west.id
  subnet_id      = aws_subnet.subnet-jump-it-west.id
}
# associate igw route table to the tgw subnet
resource "aws_route_table_association" "rtb-asctn-igw-tgw-it-west" {
  provider = aws.provider-2
  route_table_id = aws_route_table.rtb-igw-it-west.id
  subnet_id      = aws_subnet.subnet-tgw-it-west.id
}

############# SG #############
# Define security-group jump
resource "aws_security_group" "sg-jump-it-west" {
  provider = aws.provider-2
  vpc_id = aws_vpc.vpc-it-west.id
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
    Name = format("sg-jump-it-west")
  }
}

############# NACL #############
resource "aws_network_acl" "nacl-it-west" {
  provider = aws.provider-2
  vpc_id = aws_vpc.vpc-it-west.id
  subnet_ids = [
    aws_subnet.subnet-jump-it-west.id
  ]
  ingress {
    protocol   = "tcp"
    rule_no    = 10
    action     = "allow"
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
    Name = format("nacl-it-west")
  }
}

resource "aws_network_acl" "nacl-tgw-it-west" {
  provider = aws.provider-2
  vpc_id = aws_vpc.vpc-it-west.id
  subnet_ids = [
    aws_subnet.subnet-tgw-it-west.id
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
    Name = format("nacl-tgw-it-west")
  }
}
#################### instances ####################
# Create EC2 linux instance - jump
resource "aws_instance" "jump-vpc-it-west" {
  provider = aws.provider-2
  count = 1
  ami = var.california-ec2-instance-ami
  instance_type = var.california-ec2-instance-type
  key_name = aws_key_pair.provider-2-ec2key.key_name
  subnet_id = aws_subnet.subnet-jump-it-west.id
  private_ip = "10.4.1.100"
  vpc_security_group_ids = [aws_security_group.sg-jump-it-west.id]
  depends_on = [aws_internet_gateway.igw-it-west]
  user_data = file(var.update-server)
  tags = {
    Name =  format("jump%s-it-west", count.index+1)
  }
}
resource "aws_instance" "test-vpc-it-west" {
  provider = aws.provider-2
  count = 1
  ami = var.california-ec2-instance-ami
  instance_type = var.california-ec2-instance-type
  key_name = aws_key_pair.provider-2-ec2key.key_name
  subnet_id = aws_subnet.subnet-jump-it-west.id
  private_ip = "10.4.1.101"
  vpc_security_group_ids = [aws_security_group.sg-jump-it-west.id]
  depends_on = [aws_internet_gateway.igw-it-west]
  user_data = file(var.update-server)
  tags = {
    Name =  format("test%s-it-west", count.index+1)
  }
}
resource "aws_instance" "vpn-vpc-it-west" {
  provider = aws.provider-2
  count = 1
  ami = var.california-ec2-instance-ami
  instance_type = var.california-ec2-instance-type
  key_name = aws_key_pair.provider-2-ec2key.key_name
  subnet_id = aws_subnet.subnet-jump-it-west.id
  private_ip = "10.4.1.102"
  vpc_security_group_ids = [aws_security_group.sg-jump-it-west.id]
  depends_on = [aws_internet_gateway.igw-it-west]
  user_data = file(var.update-server)
  tags = {
    Name =  format("vpn%s-it-west", count.index+1)
  }
}

#################### TGW ####################
# Create TGW
resource "aws_ec2_transit_gateway" "tgw-west" {
provider = aws.provider-2
  tags = {
        Name = format("tgw-west")
    }
}
# TGW to vpc-hr-west attachement
resource "aws_ec2_transit_gateway_vpc_attachment" "tgw-att-hr-west" {
  provider = aws.provider-2
  subnet_ids         = [aws_subnet.subnet-tgw-hr-west.id]
  depends_on         = [aws_subnet.subnet-tgw-hr-west]
  transit_gateway_id = aws_ec2_transit_gateway.tgw-west.id
  vpc_id             = aws_vpc.vpc-hr-west.id
  tags               = {
    Name = format("tgw-att-hr-west")
  }
}
# TGW to vpc-it-west attachement
resource "aws_ec2_transit_gateway_vpc_attachment" "tgw-att-it-west" {
  provider = aws.provider-2
  subnet_ids         = [aws_subnet.subnet-tgw-it-west.id]
  depends_on         = [aws_subnet.subnet-tgw-it-west]
  transit_gateway_id = aws_ec2_transit_gateway.tgw-west.id
  vpc_id             = aws_vpc.vpc-it-west.id
  tags               = {
    Name = format("tgw-att-it-west")
  }
}

// #################### VPC Peering ####################
# vpc peering between vpc hr west & east
# Requester
resource "aws_vpc_peering_connection" "pcx-hr-west-east-r" {
  provider = aws.provider-2
  vpc_id        = aws_vpc.vpc-hr-west.id
  peer_vpc_id   = aws_vpc.vpc-hr-east.id
  peer_owner_id = data.aws_caller_identity.current.account_id
  peer_region   = var.region-1
  auto_accept   = false
  tags = {
    Name = "pcx-hr-west-east-r"
  }
}
# Accepter
resource "aws_vpc_peering_connection_accepter" "pcx-hr-east-west-a" {
  provider = aws.provider-1
  vpc_peering_connection_id = aws_vpc_peering_connection.pcx-hr-west-east-r.id
  auto_accept               = true
  tags = {
    Name = "pcx-hr-east-west-a"
  }
}

# vpc peering between vpc it west & hr east
# Requester
resource "aws_vpc_peering_connection" "pcx-it-west-hr-east-r" {
  provider = aws.provider-2
  vpc_id        = aws_vpc.vpc-it-west.id
  peer_vpc_id   = aws_vpc.vpc-hr-east.id
  peer_owner_id = data.aws_caller_identity.current.account_id
  peer_region   = var.region-1
  auto_accept   = false
  tags = {
    Name = "pcx-it-west-hr-east-r"
  }
}
# Accepter
resource "aws_vpc_peering_connection_accepter" "pcx-hr-east-it-west-a" {
  provider = aws.provider-1
  vpc_peering_connection_id = aws_vpc_peering_connection.pcx-it-west-hr-east-r.id
  auto_accept               = true
  tags = {
    Name = "pcx-hr-east-it-west-a"
  }
}

# vpc peering between vpc it west & finance east
# Requester
resource "aws_vpc_peering_connection" "pcx-it-west-fin-east-r" {
  provider = aws.provider-2
  vpc_id        = aws_vpc.vpc-it-west.id
  peer_vpc_id   = aws_vpc.vpc-fin-east.id
  peer_owner_id = data.aws_caller_identity.current.account_id
  peer_region   = var.region-1
  auto_accept   = false
  tags = {
    Name = "pcx-it-west-fin-east-r"
  }
}
# Accepter
resource "aws_vpc_peering_connection_accepter" "pcx-fin-east-it-west-a" {
  provider = aws.provider-1
  vpc_peering_connection_id = aws_vpc_peering_connection.pcx-it-west-fin-east-r.id
  auto_accept               = true
  tags = {
    Name = "pcx-fin-east-it-west-a"
  }
}
