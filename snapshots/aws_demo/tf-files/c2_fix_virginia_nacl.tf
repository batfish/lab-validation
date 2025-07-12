#################### Provider ####################
# Define provider
provider "aws" {
  profile = var.profile
  region  = var.region-1
}
provider "aws" {
  profile = var.profile
  alias = "provider-1"
  region  = var.region-1
}
# Use existing ssh key pair
resource "aws_key_pair" "provider-1-ec2key" {
  provider = aws.provider-1
  key_name = "publicKey"
  public_key = file(var.public-key-path)
}
# Declare the AZ data source
data "aws_availability_zones" "az-provider-1" {
  provider = aws.provider-1
  state = "available"
}
######################################## vpc-hr-east ########################################
#################### vpc ####################
# Define VPC
resource "aws_vpc" "vpc-hr-east" {
  provider = aws.provider-1
  cidr_block = var.cidr-hr-east
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = var.vpc-hr-east
  }
}

#################### subnet ####################
# Define public subnet
resource "aws_subnet" "subnet-public-hr-east" {
  provider = aws.provider-1
  vpc_id     = aws_vpc.vpc-hr-east.id
  cidr_block = var.subnet-public-hr-east
  availability_zone = data.aws_availability_zones.az-provider-1.names[0]
  tags = {
    Name = format("subnet-public-hr-east")
  }
}
# Define web subnet
resource "aws_subnet" "subnet-web-hr-east" {
  provider = aws.provider-1
  vpc_id     = aws_vpc.vpc-hr-east.id
  cidr_block = var.subnet-web-hr-east
  availability_zone = data.aws_availability_zones.az-provider-1.names[0]
  tags = {
    Name = format("subnet-web-hr-east")
  }
}
# Define db subnet
resource "aws_subnet" "subnet-db-hr-east" {
  provider = aws.provider-1
  vpc_id     = aws_vpc.vpc-hr-east.id
  cidr_block = var.subnet-db-hr-east
  availability_zone = data.aws_availability_zones.az-provider-1.names[0]
  tags = {
    Name = format("subnet-db-hr-east")
  }
}
# Define tgw subnet
resource "aws_subnet" "subnet-tgw-hr-east" {
  provider = aws.provider-1
  vpc_id     = aws_vpc.vpc-hr-east.id
  cidr_block = var.subnet-tgw-hr-east
  availability_zone = data.aws_availability_zones.az-provider-1.names[0]
  tags = {
    Name = format("subnet-tgw-hr-east")
  }
}
#################### igw-ngw ####################
# Define igw
resource "aws_internet_gateway" "igw-hr-east" {
  provider = aws.provider-1
  vpc_id = aws_vpc.vpc-hr-east.id
  tags = {
    Name = format("igw-hr-east")
  }
}
# Define elastic ip for ngw
resource "aws_eip" "eip-ngw-hr-east" {
  provider = aws.provider-1
  vpc = true
    tags = {
    Name = format("eip-ngw-hr-east")
  }
}
# Define ngw
resource "aws_nat_gateway" "ngw-hr-east" {
  provider = aws.provider-1
  allocation_id = aws_eip.eip-ngw-hr-east.id
  subnet_id     = aws_subnet.subnet-public-hr-east.id
  depends_on = [aws_internet_gateway.igw-hr-east]
    tags = {
    Name = format("ngw-hr-east")
  }
}

#################### route tables ####################
# Define route table  - igw
resource "aws_route_table" "rtb-igw-hr-east" {
  provider = aws.provider-1
  vpc_id = aws_vpc.vpc-hr-east.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw-hr-east.id
  }
  route {
    cidr_block = "10.2.0.0/16"
    transit_gateway_id = aws_ec2_transit_gateway.tgw-east.id
  }
  route {
    cidr_block = "10.3.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-hr-west-east-r.id
  }
  route {
    cidr_block = "10.4.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-it-west-hr-east-r.id
  }
  tags = {
    Name = format("rtb-igw-hr-east")
  }
}
# associate igw route table to the public subnet
resource "aws_route_table_association" "rtb-asctn-igw-public-hr-east" {
  provider = aws.provider-1
  route_table_id = aws_route_table.rtb-igw-hr-east.id
  subnet_id      = aws_subnet.subnet-public-hr-east.id
}
# Define route table  - ngw
resource "aws_route_table" "rtb-ngw-hr-east" {
  provider = aws.provider-1
  vpc_id = aws_vpc.vpc-hr-east.id
  route {
    cidr_block = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.ngw-hr-east.id
  }
  route {
    cidr_block = "10.2.0.0/16"
    transit_gateway_id = aws_ec2_transit_gateway.tgw-east.id
  }
  route {
    cidr_block = "10.3.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-hr-west-east-r.id
  }
  route {
    cidr_block = "10.4.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-it-west-hr-east-r.id
  }
  tags = {
    Name = format("rtb-ngw-hr-east")
  }
}
# associate ngw route table to the db subnet
resource "aws_route_table_association" "rtb-asctn-ngw-db-hr-east" {
  provider = aws.provider-1
  route_table_id = aws_route_table.rtb-ngw-hr-east.id
  subnet_id      = aws_subnet.subnet-db-hr-east.id
}
# associate ngw route table to the web subnet
resource "aws_route_table_association" "rtb-asctn-ngw-web-hr-east" {
  provider = aws.provider-1
  route_table_id = aws_route_table.rtb-ngw-hr-east.id
  subnet_id      = aws_subnet.subnet-web-hr-east.id
}
# associate ngw route table to the tgw subnet
resource "aws_route_table_association" "rtb-asctn-ngw-tgw-hr-east" {
  provider = aws.provider-1
  route_table_id = aws_route_table.rtb-ngw-hr-east.id
  subnet_id      = aws_subnet.subnet-tgw-hr-east.id
}

############# SG #############
# Define security-group web
resource "aws_security_group" "sg-web-hr-east" {
  provider = aws.provider-1
  vpc_id = aws_vpc.vpc-hr-east.id
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
    Name = format("sg-web-hr-east")
  }
}
# Define security-group db
resource "aws_security_group" "sg-db-hr-east" {
  provider = aws.provider-1
  vpc_id = aws_vpc.vpc-hr-east.id
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
    Name = format("sg-db-hr-east")
  }
}

############# SG #############
resource "aws_network_acl" "nacl-hr-east" {
  provider = aws.provider-1
  vpc_id = aws_vpc.vpc-hr-east.id
  subnet_ids = [
    aws_subnet.subnet-web-hr-east.id,
    aws_subnet.subnet-db-hr-east.id
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
    Name = format("nacl-hr-east")
  }
}

resource "aws_network_acl" "nacl-tgw-hr-east" {
  provider = aws.provider-1
  vpc_id = aws_vpc.vpc-hr-east.id
  subnet_ids = [
    aws_subnet.subnet-tgw-hr-east.id
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
    Name = format("nacl-tgw-hr-east")
  }
}

#################### instances ####################
# Create EC2 linux instance - web
resource "aws_instance" "web-vpc-hr-east" {
  provider = aws.provider-1
  count = 2
  ami = var.virginia-ec2-instance-ami
  instance_type = var.virginia-ec2-instance-type
  key_name = aws_key_pair.provider-1-ec2key.key_name
  subnet_id = aws_subnet.subnet-web-hr-east.id
  vpc_security_group_ids = [aws_security_group.sg-web-hr-east.id]
  depends_on = [aws_internet_gateway.igw-hr-east]
  user_data = file(var.create-web-server)
  tags = {
    Name =  format("web%s-hr-east", count.index+1)
  }
}
# Create EC2 linux instance - db
resource "aws_instance" "db-vpc-hr-east" {
  provider = aws.provider-1
  count = 1
  ami = var.virginia-ec2-instance-ami
  instance_type = var.virginia-ec2-instance-type
  key_name = aws_key_pair.provider-1-ec2key.key_name
  subnet_id = aws_subnet.subnet-db-hr-east.id
  vpc_security_group_ids = [aws_security_group.sg-db-hr-east.id]
  depends_on = [aws_nat_gateway.ngw-hr-east]
  user_data = file(var.update-server)
  tags = {
    Name =  format("db%s-hr-east", count.index+1)
  }
}

#################### NLB ####################
# Define elastic ip for nlb
resource "aws_eip" "eip-nlb-hr-east" {
  provider = aws.provider-1
  vpc = true
    tags = {
    Name = format("eip-nlb-hr-east")
  }
}
resource "aws_lb" "nlb-web-hr-east" {
  name = "nlb-web-hr-east"
  provider = aws.provider-1
  internal           = false
  load_balancer_type = "network"
  subnet_mapping {
  subnet_id     = aws_subnet.subnet-public-hr-east.id
  allocation_id = aws_eip.eip-nlb-hr-east.id
}
  tags = {
    Name =  format("nlb-web-hr-east")
  }
}
resource "aws_lb_target_group" "nlb-web-http-tg-hr-east" {
  provider = aws.provider-1
  port     = 80
  protocol = "TCP"
  vpc_id   = aws_vpc.vpc-hr-east.id
  stickiness {
    enabled = false
    type = "lb_cookie"
  }
}
resource "aws_lb_listener" "nlb-web-http-lsntr-hr-east" {
  provider = aws.provider-1
  load_balancer_arn = aws_lb.nlb-web-hr-east.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.nlb-web-http-tg-hr-east.arn
  }
}
resource "aws_lb_target_group_attachment" "nlb-web-http-tg-atchmnt-hr-east" {
  count = 2
  provider = aws.provider-1
  target_group_arn = aws_lb_target_group.nlb-web-http-tg-hr-east.arn
  target_id        = aws_instance.web-vpc-hr-east[count.index].id
  port             = 80
}

resource "aws_lb_target_group" "nlb-web-https-tg-hr-east" {
  provider = aws.provider-1
  port     = 443
  protocol = "TCP"
  vpc_id   = aws_vpc.vpc-hr-east.id
  stickiness {
    enabled = false
    type = "lb_cookie"
  }
}
resource "aws_lb_listener" "nlb-web-https-lsntr-hr-east" {
  provider = aws.provider-1
  load_balancer_arn = aws_lb.nlb-web-hr-east.arn
  port              = 443
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.nlb-web-https-tg-hr-east.arn
  }
}
resource "aws_lb_target_group_attachment" "nlb-web-https-tg-atchmnt-hr-east" {
  count = 2
  provider = aws.provider-1
  target_group_arn = aws_lb_target_group.nlb-web-https-tg-hr-east.arn
  target_id        = aws_instance.web-vpc-hr-east[count.index].id
  port             = 443
}


######################################## vpc-fin-east ########################################
#################### vpc ####################
# Define VPC
resource "aws_vpc" "vpc-fin-east" {
  provider = aws.provider-1
  cidr_block = var.cidr-fin-east
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = var.vpc-fin-east
  }
}

#################### subnet ####################
# Define web subnet
resource "aws_subnet" "subnet-expenses-fin-east" {
  provider = aws.provider-1
  vpc_id     = aws_vpc.vpc-fin-east.id
  cidr_block = var.subnet-expenses-fin-east
  availability_zone = data.aws_availability_zones.az-provider-1.names[0]
  tags = {
    Name = format("subnet-expenses-fin-east")
  }
}
# Define db subnet
resource "aws_subnet" "subnet-db-fin-east" {
  provider = aws.provider-1
  vpc_id     = aws_vpc.vpc-fin-east.id
  cidr_block = var.subnet-db-fin-east
  availability_zone = data.aws_availability_zones.az-provider-1.names[0]
  tags = {
    Name = format("subnet-db-fin-east")
  }
}
# Define tgw subnet
resource "aws_subnet" "subnet-tgw-fin-east" {
  provider = aws.provider-1
  vpc_id     = aws_vpc.vpc-fin-east.id
  cidr_block = var.subnet-tgw-fin-east
  availability_zone = data.aws_availability_zones.az-provider-1.names[0]
  tags = {
    Name = format("subnet-tgw-fin-east")
  }
}
#################### route tables ####################
# Define route table
resource "aws_route_table" "rtb-fin-east" {
  provider = aws.provider-1
  vpc_id = aws_vpc.vpc-fin-east.id
  route {
    cidr_block = "10.1.0.0/16"
    transit_gateway_id = aws_ec2_transit_gateway.tgw-east.id
  }
  route {
    cidr_block = "10.4.0.0/16"
    vpc_peering_connection_id = aws_vpc_peering_connection.pcx-it-west-fin-east-r.id
  }
  tags = {
    Name = format("rtb-fin-east")
  }
}
# associate the route table to expense subnet
resource "aws_route_table_association" "rtb-asctn-expenses-fin-east" {
  provider = aws.provider-1
  route_table_id = aws_route_table.rtb-fin-east.id
  subnet_id      = aws_subnet.subnet-expenses-fin-east.id
}
# associate the route table to db subnet
resource "aws_route_table_association" "rtb-asctn-db-fin-east" {
  provider = aws.provider-1
  route_table_id = aws_route_table.rtb-fin-east.id
  subnet_id      = aws_subnet.subnet-db-fin-east.id
}
# associate the route table to tgw subnet
resource "aws_route_table_association" "rtb-asctn-tgw-fin-east" {
  provider = aws.provider-1
  route_table_id = aws_route_table.rtb-fin-east.id
  subnet_id      = aws_subnet.subnet-tgw-fin-east.id
}

############# SG #############
# Define security-group web
resource "aws_security_group" "sg-expenses-fin-east" {
  provider = aws.provider-1
  vpc_id = aws_vpc.vpc-fin-east.id
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
    Name = format("sg-expenses-fin-east")
  }
}
# Define security-group db
resource "aws_security_group" "sg-db-fin-east" {
  provider = aws.provider-1
  vpc_id = aws_vpc.vpc-fin-east.id
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
    Name = format("sg-db-fin-east")
  }
}

############# NACL #############
resource "aws_network_acl" "nacl-fin-east" {
  provider = aws.provider-1
  vpc_id = aws_vpc.vpc-fin-east.id
  subnet_ids = [
    aws_subnet.subnet-expenses-fin-east.id,
    aws_subnet.subnet-db-fin-east.id
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
    Name = format("nacl-fin-east")
  }
}

resource "aws_network_acl" "nacl-tgw-fin-east" {
  provider = aws.provider-1
  vpc_id = aws_vpc.vpc-fin-east.id
  subnet_ids = [
    aws_subnet.subnet-tgw-fin-east.id
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
    Name = format("nacl-tgw-fin-east")
  }
}

#################### instances ####################
# Create EC2 linux instance - expenses
resource "aws_instance" "expense-vpc-fin-east" {
  provider = aws.provider-1
  count = 2
  ami = var.virginia-ec2-instance-ami
  instance_type = var.virginia-ec2-instance-type
  key_name = aws_key_pair.provider-1-ec2key.key_name
  subnet_id = aws_subnet.subnet-expenses-fin-east.id
  depends_on = [aws_subnet.subnet-expenses-fin-east]
  vpc_security_group_ids = [aws_security_group.sg-expenses-fin-east.id]
  user_data = file(var.create-web-server)
  tags = {
    Name =  format("expenses%s-fin-east", count.index+1)
  }
}
# Create EC2 linux instance - db
resource "aws_instance" "db-vpc-fin-east" {
  provider = aws.provider-1
  count = 1
  ami = var.virginia-ec2-instance-ami
  instance_type = var.virginia-ec2-instance-type
  key_name = aws_key_pair.provider-1-ec2key.key_name
  subnet_id = aws_subnet.subnet-db-fin-east.id
  depends_on = [aws_subnet.subnet-db-fin-east]
  vpc_security_group_ids = [aws_security_group.sg-db-fin-east.id]
  user_data = file(var.update-server)
  tags = {
    Name =  format("db%s-fin-east", count.index+1)
  }
}

#################### NLB ####################
resource "aws_lb" "nlb-fin-east" {
  name = "nlb-fin-east"
  provider = aws.provider-1
  internal           = true
  load_balancer_type = "network"
  subnets            = [aws_subnet.subnet-expenses-fin-east.id]
  tags = {
    Name =  format("nlb-fin-east")
  }
}
resource "aws_lb_target_group" "nlb-web-http-tg-fin-east" {
  provider = aws.provider-1
  port     = 80
  protocol = "TCP"
  vpc_id   = aws_vpc.vpc-fin-east.id
  stickiness {
    enabled = false
    type = "lb_cookie"
  }
}
resource "aws_lb_listener" "nlb-web-http-lsntr-fin-east" {
  provider = aws.provider-1
  load_balancer_arn = aws_lb.nlb-fin-east.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.nlb-web-http-tg-fin-east.arn
  }
}
resource "aws_lb_target_group_attachment" "nlb-web-http-tg-atchmnt-fin-east" {
  count = 2
  provider = aws.provider-1
  target_group_arn = aws_lb_target_group.nlb-web-http-tg-fin-east.arn
  target_id        = aws_instance.expense-vpc-fin-east[count.index].id
  port             = 80
}

resource "aws_lb_target_group" "nlb-web-https-tg-fin-east" {
  provider = aws.provider-1
  port     = 443
  protocol = "TCP"
  vpc_id   = aws_vpc.vpc-fin-east.id
  stickiness {
    enabled = false
    type = "lb_cookie"
  }
}
resource "aws_lb_listener" "nlb-web-https-lsntr-fin-east" {
  provider = aws.provider-1
  load_balancer_arn = aws_lb.nlb-fin-east.arn
  port              = 443
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.nlb-web-https-tg-fin-east.arn
  }
}
resource "aws_lb_target_group_attachment" "nlb-web-https-tg-atchmnt-fin-east" {
  count = 2
  provider = aws.provider-1
  target_group_arn = aws_lb_target_group.nlb-web-https-tg-fin-east.arn
  target_id        = aws_instance.expense-vpc-fin-east[count.index].id
  port             = 443
}

// #################### TGW ####################
# Create TGW
resource "aws_ec2_transit_gateway" "tgw-east" {
provider = aws.provider-1
  tags = {
        Name = format("tgw-east")
    }
}
# TGW to vpc-hr-east attachement
resource "aws_ec2_transit_gateway_vpc_attachment" "tgw-att-hr-east" {
  provider = aws.provider-1
  subnet_ids         = [aws_subnet.subnet-tgw-hr-east.id]
  depends_on         = [aws_subnet.subnet-tgw-hr-east]
  transit_gateway_id = aws_ec2_transit_gateway.tgw-east.id
  vpc_id             = aws_vpc.vpc-hr-east.id
  tags               = {
    Name = format("tgw-att-hr-east")
  }
}
# TGW to vpc-fin-east attachement
resource "aws_ec2_transit_gateway_vpc_attachment" "tgw-att-fin-east" {
  provider = aws.provider-1
  subnet_ids         = [aws_subnet.subnet-tgw-fin-east.id]
  depends_on         = [aws_subnet.subnet-tgw-fin-east]
  transit_gateway_id = aws_ec2_transit_gateway.tgw-east.id
  vpc_id             = aws_vpc.vpc-fin-east.id
  tags               = {
    Name = format("tgw-att-fin-east")
  }
}
