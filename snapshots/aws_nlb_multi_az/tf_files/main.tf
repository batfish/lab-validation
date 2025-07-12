
##### providers
provider "aws" {
  region  = var.region
  profile = var.profile
}

##### VPC
resource "aws_vpc" "example" {
  cidr_block            = var.cidr
  enable_dns_support    = true
  enable_dns_hostnames  = true
  tags = merge(
    {
      "Name" = format("example")
    },
    var.tags
  )
}

##### Subnets
resource "aws_subnet" "example-jump-subnet" {
  vpc_id            = aws_vpc.example.id
  cidr_block        = var.jump_cidr
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = merge(
    {
      Name = format("example-jump-subnet")
    },
    var.tags
  )
}
resource "aws_subnet" "example-public-subnet-az-1" {
  vpc_id            = aws_vpc.example.id
  cidr_block        = var.public_cidr_az_1
  map_public_ip_on_launch = "true"
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = merge(
    {
      Name = format("example-public-subnet-az-1")
    },
    var.tags
  )
}
resource "aws_subnet" "example-public-subnet-az-2" {
  vpc_id            = aws_vpc.example.id
  cidr_block        = var.public_cidr_az_2
  map_public_ip_on_launch = "true"
  availability_zone = data.aws_availability_zones.az.names[1]
  tags = merge(
    {
      Name = format("example-public-subnet-az-2")
    },
    var.tags
  )
}
resource "aws_subnet" "example-private-subnet-az-1" {
  vpc_id            = aws_vpc.example.id
  cidr_block        = var.private_cidr_az_1
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = merge(
    {
      Name = format("example-private-subnet-az-1")
    },
    var.tags
  )
}
resource "aws_subnet" "example-private-subnet-az-2" {
  vpc_id            = aws_vpc.example.id
  cidr_block        = var.private_cidr_az_2
  availability_zone = data.aws_availability_zones.az.names[1]
  tags = merge(
    {
      Name = format("example-private-subnet-az-2")
    },
    var.tags
  )
}
resource "aws_subnet" "example-private-subnet-az-3" {
  vpc_id            = aws_vpc.example.id
  cidr_block        = var.private_cidr_az_3
  availability_zone = data.aws_availability_zones.az.names[2]
  tags = merge(
    {
      Name = format("example-private-subnet-az-3")
    },
    var.tags
  )
}

##### IGW
resource "aws_internet_gateway" "example-igw" {
  vpc_id  = aws_vpc.example.id
  tags = merge(
    {
      Name = format("example-igw")
    },
    var.tags
  )
}

##### NGW
resource "aws_eip" "example-ngw-eip" {
  vpc = true
  tags = merge(
    {
      Name = format("example-ngw-eip")
    },
    var.tags
  )
}
resource "aws_nat_gateway" "example-ngw" {
  allocation_id = aws_eip.example-ngw-eip.id
  subnet_id     = aws_subnet.example-public-subnet-az-1.id
  depends_on    = [aws_internet_gateway.example-igw]
  tags = merge(
    {
      Name = format("example-ngw")
    },
    var.tags
  )
}

##### Route table
resource "aws_route_table" "example-public-rtb" {
  vpc_id  = aws_vpc.example.id
  route {
    cidr_block = var.any_subnet
    gateway_id = aws_internet_gateway.example-igw.id
  }
  tags = merge(
    {
      Name = format("example-public-rtb")
    },
    var.tags
  )
}
resource "aws_route_table_association" "example-jump-subnet" {
  route_table_id = aws_route_table.example-public-rtb.id
  subnet_id      = aws_subnet.example-jump-subnet.id
}
resource "aws_route_table_association" "example-public-subnet-az-1" {
  route_table_id = aws_route_table.example-public-rtb.id
  subnet_id      = aws_subnet.example-public-subnet-az-1.id
}
resource "aws_route_table_association" "example-public-subnet-az-2" {
  route_table_id = aws_route_table.example-public-rtb.id
  subnet_id      = aws_subnet.example-public-subnet-az-2.id
}

##### Route table
resource "aws_route_table" "example-private-rtb" {
  vpc_id  = aws_vpc.example.id
  route {
    cidr_block      = var.any_subnet
    nat_gateway_id  = aws_nat_gateway.example-ngw.id
  }
  tags = merge(
    {
      Name = format("example-private-rtb")
    },
    var.tags
  )
}
resource "aws_route_table_association" "example-private-subnet-az-1" {
  route_table_id = aws_route_table.example-private-rtb.id
  subnet_id      = aws_subnet.example-private-subnet-az-1.id
}
resource "aws_route_table_association" "example-private-subnet-az-2" {
  route_table_id = aws_route_table.example-private-rtb.id
  subnet_id      = aws_subnet.example-private-subnet-az-2.id
}
resource "aws_route_table_association" "example-private-subnet-az-3" {
  route_table_id = aws_route_table.example-private-rtb.id
  subnet_id      = aws_subnet.example-private-subnet-az-3.id
}

##### NACL
resource "aws_network_acl" "example-public-nacl" {
  vpc_id = aws_vpc.example.id
  subnet_ids = [
    aws_subnet.example-jump-subnet.id,
    aws_subnet.example-public-subnet-az-1.id,
    aws_subnet.example-public-subnet-az-2.id
  ]
  ingress {
    protocol   = "-1"
    rule_no    = 1000
    action     = "allow"
    cidr_block = var.any_subnet
    from_port  = 0
    to_port    = 0
  }
  egress {
    protocol   = "-1"
    rule_no    = 1000
    action     = "allow"
    cidr_block = var.any_subnet
    from_port  = 0
    to_port    = 0
  }
  tags = merge(
    {
      Name = format("example-public-nacl")
    },
    var.tags
  )
}
resource "aws_network_acl" "example-private-nacl" {
  vpc_id = aws_vpc.example.id
  subnet_ids = [
    aws_subnet.example-private-subnet-az-1.id,
    aws_subnet.example-private-subnet-az-2.id
  ]
  ingress {
    protocol   = "tcp"
    rule_no    = 10
    action     = "allow"
    cidr_block = var.jump_host
    from_port  = 22
    to_port    = 22
  }
  ingress {
    protocol   = "tcp"
    rule_no    = 20
    action     = "deny"
    cidr_block = var.any_subnet
    from_port  = 22
    to_port    = 22
  }
  ingress {
    protocol   = "-1"
    rule_no    = 1000
    action     = "allow"
    cidr_block = var.any_subnet
    from_port  = 0
    to_port    = 0
  }
  egress {
    protocol   = "-1"
    rule_no    = 1000
    action     = "allow"
    cidr_block = var.any_subnet
    from_port  = 0
    to_port    = 0
  }
  tags = merge(
    {
      Name = format("example-private-nacl")
    },
    var.tags
  )
}

##### Security Group
resource "aws_security_group" "example-jump-sg" {
  vpc_id = aws_vpc.example.id
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.any_subnet]
    description = "SSH Access"
  }
  ingress {
    from_port   = 8
    to_port     = 0
    protocol    = "icmp"
    cidr_blocks = [var.any_subnet]
    description = "ICMP Echo Request Access"
  }
  ingress {
    from_port   = 33434
    to_port     = 33534
    protocol    = "udp"
    cidr_blocks = [var.any_subnet]
    description = "Traceroute Access"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.any_subnet]
    description = "Allow all"
  }
  tags = merge(
    {
      Name = format("example-jump-sg")
    },
    var.tags
  )
}
resource "aws_security_group" "example-public-sg" {
  vpc_id = aws_vpc.example.id
  # SSH access is controlled at NACL
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.any_subnet]
    description = "Allow all"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.any_subnet]
    description = "Allow all"
  }
  tags = merge(
    {
      Name = format("example-public-sg")
    },
    var.tags
  )
}
resource "aws_security_group" "example-private-sg" {
  vpc_id = aws_vpc.example.id
  # SSH access is controlled at NACL
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.any_subnet]
    description = "SSH Access"
  }
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [var.any_subnet]
    description = "HTTP Access"
  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.any_subnet]
    description = "HTTPS Access"
  }
  ingress {
    from_port   = 8
    to_port     = 0
    protocol    = "icmp"
    cidr_blocks = [var.any_subnet]
    description = "ICMP Access"
  }
  ingress {
    from_port   = 33434
    to_port     = 33534
    protocol    = "udp"
    cidr_blocks = [var.any_subnet]
    description = "Traceroute Access"
  }
 egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.any_subnet]
    description = "Allow all"
  }
  tags = merge(
    {
      Name = format("example-private-sg")
    },
    var.tags
  )
}

##### SSH key pair
resource "aws_key_pair" "example-this" {
  key_name    = format("example-PubKey")
  public_key  = file(var.public_key_path)
}


#### jump instances
resource "aws_instance" "example-jump" {
  ami                         = var.ami
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.example-this.key_name
  subnet_id                   = aws_subnet.example-jump-subnet.id
  private_ip                  = var.jump_host_private_ip
  vpc_security_group_ids      = [aws_security_group.example-jump-sg.id]
  depends_on                  = [aws_internet_gateway.example-igw]
  user_data                   = file(var.update_server)
  associate_public_ip_address = "true"
  tags = merge(
    {
      Name = format("example-jump")
    },
    var.tags
  )
}

##### private instances
resource "aws_instance" "target-az1" {
  count                       = 1
  ami                         = var.ami
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.example-this.key_name
  subnet_id                   = aws_subnet.example-private-subnet-az-1.id
  vpc_security_group_ids      = [aws_security_group.example-private-sg.id]
  depends_on                  = [aws_nat_gateway.example-ngw]
  user_data                   = file(var.create_web_server)
  tags = merge(
    {
      Name = format("example-target-az1")
    },
    var.tags
  )
}
resource "aws_instance" "target-az2" {
  count                       = 1
  ami                         = var.ami
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.example-this.key_name
  subnet_id                   = aws_subnet.example-private-subnet-az-2.id
  vpc_security_group_ids      = [aws_security_group.example-private-sg.id]
  depends_on                  = [aws_nat_gateway.example-ngw]
  user_data                   = file(var.create_web_server)
  tags = merge(
    {
      Name = format("example-target-az2")
    },
    var.tags
  )
}
resource "aws_instance" "target-az-different" {
  count                       = 1
  ami                         = var.ami
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.example-this.key_name
  subnet_id                   = aws_subnet.example-private-subnet-az-3.id
  vpc_security_group_ids      = [aws_security_group.example-private-sg.id]
  depends_on                  = [aws_nat_gateway.example-ngw]
  user_data                   = file(var.create_web_server)
  tags = merge(
    {
      Name = format("example-target-az-different")
    },
    var.tags
  )
}
resource "aws_instance" "nlb-eni-private-subnet" {
  count                       = 1
  ami                         = var.ami
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.example-this.key_name
  subnet_id                   = aws_subnet.example-private-subnet-az-1.id
  vpc_security_group_ids      = [aws_security_group.example-private-sg.id]
  depends_on                  = [aws_nat_gateway.example-ngw]
  user_data                   = file(var.create_web_server)
  tags = merge(
    {
      Name = format("example-nlb-eni-private-subnet")
    },
    var.tags
  )
}

##### NLB
# working nlb
resource "aws_lb" "example-nlb-ip" {
  name = "example-nlb-ip"
  internal                          = false
  load_balancer_type                = "network"
  enable_cross_zone_load_balancing  = true
  subnets                           = [
    aws_subnet.example-public-subnet-az-1.id,
    aws_subnet.example-public-subnet-az-2.id
  ]
  tags = merge(
    {
      Name = format("example-nlb-ip")
    },
    var.tags
  )
}
resource "aws_lb_target_group" "example-nlb-ip" {
  name = "example-nlb-ip"
  port        = 80
  protocol    = "TCP"
  target_type = "ip"
  vpc_id      = aws_vpc.example.id
}
resource "aws_lb_listener" "example-nlb-ip" {
  load_balancer_arn = aws_lb.example-nlb-ip.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.example-nlb-ip.arn
  }
}
resource "aws_lb_target_group_attachment" "example-nlb-ip-1" {
  count            = 1
  target_group_arn = aws_lb_target_group.example-nlb-ip.arn
  target_id        = aws_instance.target-az1[count.index].private_ip
  port             = 80
}
resource "aws_lb_target_group_attachment" "example-nlb-ip-2" {
  count            = 1
  target_group_arn = aws_lb_target_group.example-nlb-ip.arn
  target_id        = aws_instance.target-az2[count.index].private_ip
  port             = 80
}

# target-az-different - nlb not working as target az is different than nlb az
resource "aws_lb" "example-target-az-different" {
  name = "example-target-az-different"
  internal                          = false
  load_balancer_type                = "network"
  enable_cross_zone_load_balancing  = true
  subnets                           = [
    aws_subnet.example-public-subnet-az-1.id,
    aws_subnet.example-public-subnet-az-2.id
  ]
  tags = merge(
    {
      Name = format("example-target-az-different")
    },
    var.tags
  )
}
resource "aws_lb_target_group" "example-target-az-different" {
  name = "example-target-az-different"
  port        = 80
  protocol    = "TCP"
  target_type = "ip"
  vpc_id      = aws_vpc.example.id
}
resource "aws_lb_listener" "example-target-az-different" {
  load_balancer_arn = aws_lb.example-target-az-different.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.example-target-az-different.arn
  }
}
resource "aws_lb_target_group_attachment" "example-target-az-different" {
  count            = 1
  target_group_arn = aws_lb_target_group.example-target-az-different.arn
  target_id        = aws_instance.target-az-different[count.index].private_ip
  port             = 80
}

#nlb-eni-private-subnet - nlb not working as nlb eni is in private subnet which will use NGW for internet traffic
resource "aws_lb" "example-nlb-eni-private-subnet" {
  name = "example-nlb-eni-private-subnet"
  internal                          = false
  load_balancer_type                = "network"
  enable_cross_zone_load_balancing  = true
  subnets                           = [
    aws_subnet.example-private-subnet-az-1.id
  ]
  tags = merge(
    {
      Name = format("example-nlb-eni-private-subnet")
    },
    var.tags
  )
}
resource "aws_lb_target_group" "example-nlb-eni-private-subnet" {
  name = "example-nlb-eni-private-subnet"
  port        = 80
  protocol    = "TCP"
  target_type = "ip"
  vpc_id      = aws_vpc.example.id
}
resource "aws_lb_listener" "example-nlb-eni-private-subnet" {
  load_balancer_arn = aws_lb.example-nlb-eni-private-subnet.arn
  port              = 80
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.example-nlb-eni-private-subnet.arn
  }
}
resource "aws_lb_target_group_attachment" "example-nlb-eni-private-subnet" {
  count            = 1
  target_group_arn = aws_lb_target_group.example-nlb-eni-private-subnet.arn
  target_id        = aws_instance.nlb-eni-private-subnet[count.index].private_ip
  port             = 80
}
