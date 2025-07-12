
##### providers
provider "aws" {
  region  = var.region
  profile = var.profile
}

########################################
# vpc prod
########################################
##### VPC
resource "aws_vpc" "prod" {
  cidr_block            = var.prod_cidr
  enable_dns_support    = true
  enable_dns_hostnames  = true
  tags = merge(
    {
      "Name" = format("prod")
    },
    var.prod_tags
  )
}

##### Subnets
resource "aws_subnet" "prod-jump-sub" {
  vpc_id            = aws_vpc.prod.id
  cidr_block        = var.prod_jump_cidr
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = merge(
    {
      Name = format("prod-jump-sub")
    },
    var.prod_tags
  )
}
resource "aws_subnet" "prod-pub-sub" {
  vpc_id            = aws_vpc.prod.id
  cidr_block        = var.prod_pub_cidr
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = merge(
    {
      Name = format("prod-pub-sub")
    },
    var.prod_tags
  )
}
resource "aws_subnet" "prod-priv-az1-sub" {
  vpc_id            = aws_vpc.prod.id
  cidr_block        = var.prod_priv_cidr_az1
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = merge(
    {
      Name = format("prod-priv-az1-sub")
    },
    var.prod_tags
  )
}
resource "aws_subnet" "prod-priv-az2-sub" {
  vpc_id            = aws_vpc.prod.id
  cidr_block        = var.prod_priv_cidr_az2
  availability_zone = data.aws_availability_zones.az.names[1]
  tags = merge(
    {
      Name = format("prod-priv-az2-sub")
    },
    var.prod_tags
  )
}
resource "aws_subnet" "prod-tgw-az1-sub" {
  vpc_id            = aws_vpc.prod.id
  cidr_block        = var.prod_tgw_cidr_az1
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = merge(
    {
      Name = format("prod-tgw-az1-sub")
    },
    var.prod_tags
  )
}
resource "aws_subnet" "prod-tgw-az2-sub" {
  vpc_id            = aws_vpc.prod.id
  cidr_block        = var.prod_tgw_cidr_az2
  availability_zone = data.aws_availability_zones.az.names[1]
  tags = merge(
    {
      Name = format("prod-tgw-az2-sub")
    },
    var.prod_tags
  )
}

##### IGW
resource "aws_internet_gateway" "prod-igw" {
  vpc_id  = aws_vpc.prod.id
  tags = merge(
    {
      Name = format("prod-igw")
    },
    var.prod_tags
  )
}

##### NGW
resource "aws_eip" "prod-ngw-eip" {
  vpc = true
  tags = merge(
    {
      Name = format("prod-ngw-eip")
    },
    var.prod_tags
  )
}
resource "aws_nat_gateway" "prod-ngw" {
  allocation_id = aws_eip.prod-ngw-eip.id
  subnet_id     = aws_subnet.prod-pub-sub.id
  depends_on    = [aws_internet_gateway.prod-igw]
  tags = merge(
    {
      Name = format("prod-ngw")
    },
    var.prod_tags
  )
}

##### Route table
# pub route table
resource "aws_route_table" "prod-pub-rtb" {
  vpc_id  = aws_vpc.prod.id
  route {
    cidr_block = var.any_subnet
    gateway_id = aws_internet_gateway.prod-igw.id
  }
  route {
    cidr_block          = var.dev_cidr
    transit_gateway_id  = aws_ec2_transit_gateway.tgw.id
  }
  tags = merge(
    {
      Name = format("prod-pub-rtb")
    },
    var.prod_tags
  )
}
resource "aws_route_table_association" "prod-jump-sub" {
  route_table_id = aws_route_table.prod-pub-rtb.id
  subnet_id      = aws_subnet.prod-jump-sub.id
}
resource "aws_route_table_association" "prod-pub-sub" {
  route_table_id = aws_route_table.prod-pub-rtb.id
  subnet_id      = aws_subnet.prod-pub-sub.id
}
# priv route table
resource "aws_route_table" "prod-priv-rtb" {
  vpc_id  = aws_vpc.prod.id
  route {
    cidr_block          = var.any_subnet
    nat_gateway_id      = aws_nat_gateway.prod-ngw.id
  }
  route {
    cidr_block          = var.dev_cidr
    transit_gateway_id  = aws_ec2_transit_gateway.tgw.id
  }
  tags = merge(
    {
      Name = format("prod-priv-rtb")
    },
    var.prod_tags
  )
}
resource "aws_route_table_association" "prod-priv-az1-sub" {
  route_table_id = aws_route_table.prod-priv-rtb.id
  subnet_id      = aws_subnet.prod-priv-az1-sub.id
}
resource "aws_route_table_association" "prod-priv-az2-sub" {
  route_table_id = aws_route_table.prod-priv-rtb.id
  subnet_id      = aws_subnet.prod-priv-az2-sub.id
}
resource "aws_route_table_association" "prod-tgw-az1-sub" {
  route_table_id = aws_route_table.prod-priv-rtb.id
  subnet_id      = aws_subnet.prod-tgw-az1-sub.id
}
resource "aws_route_table_association" "prod-tgw-az2-sub" {
  route_table_id = aws_route_table.prod-priv-rtb.id
  subnet_id      = aws_subnet.prod-tgw-az2-sub.id
}

##### NACL
resource "aws_network_acl" "prod-pub-nacl" {
  vpc_id = aws_vpc.prod.id
  subnet_ids = [
    aws_subnet.prod-jump-sub.id,
    aws_subnet.prod-pub-sub.id
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
      Name = format("prod-pub-nacl")
    },
    var.prod_tags
  )
}
resource "aws_network_acl" "prod-priv-nacl" {
  vpc_id = aws_vpc.prod.id
  subnet_ids = [
    aws_subnet.prod-priv-az1-sub.id,
    aws_subnet.prod-priv-az2-sub.id,
  ]
  ingress {
    protocol   = "tcp"
    rule_no    = 10
    action     = "allow"
    cidr_block = format("%s/32", var.jump_host)
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
    rule_no    = 1
    action     = "deny"
    cidr_block = format("%s/32", aws_instance.dev-priv-i1.private_ip)
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
      Name = format("prod-priv-nacl")
    },
    var.prod_tags
  )
}
resource "aws_network_acl" "prod-tgw-nacl" {
  vpc_id = aws_vpc.prod.id
  subnet_ids = [
    aws_subnet.prod-tgw-az1-sub.id,
    aws_subnet.prod-tgw-az2-sub.id,
  ]
  ingress {
    protocol   = "-1"
    rule_no    = 1
    action     = "deny"
    cidr_block = format("%s/32", aws_instance.prod-priv-i2.private_ip)
    from_port  = 0
    to_port    = 0
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
      Name = format("prod-tgw-nacl")
    },
    var.prod_tags
  )
}

##### Security Group
resource "aws_security_group" "prod-jump-sg" {
  vpc_id = aws_vpc.prod.id
  ingress {
  # SSH access is controlled at NACL
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
      Name = format("prod-jump-sg")
    },
    var.prod_tags
  )
}
resource "aws_security_group" "prod-pub-sg" {
  vpc_id = aws_vpc.prod.id
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
      Name = format("prod-pub-sg")
    },
    var.prod_tags
  )
}
resource "aws_security_group" "prod-priv-sg" {
  vpc_id = aws_vpc.prod.id
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
    cidr_blocks = [var.rfc_1918_10, var.rfc_1918_172, var.rfc_1918_192]
    description = "HTTP Access"
  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.rfc_1918_10, var.rfc_1918_172, var.rfc_1918_192]
    description = "HTTPS Access"
  }
  ingress {
    from_port   = 8
    to_port     = 0
    protocol    = "icmp"
    cidr_blocks = [var.rfc_1918_10, var.rfc_1918_172, var.rfc_1918_192]
    description = "ICMP Access"
  }
  ingress {
    from_port   = 33434
    to_port     = 33534
    protocol    = "udp"
    cidr_blocks = [var.rfc_1918_10, var.rfc_1918_172, var.rfc_1918_192]
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
      Name = format("prod-priv-sg")
    },
    var.prod_tags
  )
}

##### SSH key pair
resource "aws_key_pair" "prod-key1" {
  key_name    = format("prod-PubKey1")
  public_key  = file(var.pub_key_path)
}

##### ec2 instances
# jump
resource "aws_instance" "prod-jump" {
  count                       = 1
  ami                         = var.ami
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.prod-key1.key_name
  subnet_id                   = aws_subnet.prod-jump-sub.id
  private_ip                  = var.jump_host
  vpc_security_group_ids      = [aws_security_group.prod-jump-sg.id]
  depends_on                  = [aws_internet_gateway.prod-igw]
  user_data                   = file(var.update_server)
  associate_public_ip_address = "true"
  tags = merge(
    {
      Name = format("prod-jump%s", count.index+1)
    },
    var.prod_tags
  )
}
# priv-i1
resource "aws_instance" "prod-priv-i1" {
  ami                         = var.ami
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.prod-key1.key_name
  subnet_id                   = aws_subnet.prod-priv-az1-sub.id
  private_ip                  = "10.1.101.11"
  vpc_security_group_ids      = [aws_security_group.prod-priv-sg.id]
  depends_on                  = [aws_nat_gateway.prod-ngw]
  user_data                   = file(var.create_web_server)
  tags = merge(
    {
      Name = format("prod-priv-i1")
    },
    var.prod_tags
  )
}
# priv-i2
resource "aws_instance" "prod-priv-i2" {
  ami                         = var.ami
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.prod-key1.key_name
  subnet_id                   = aws_subnet.prod-priv-az1-sub.id
  private_ip                  = "10.1.101.12"
  vpc_security_group_ids      = [aws_security_group.prod-priv-sg.id]
  depends_on                  = [aws_nat_gateway.prod-ngw]
  user_data                   = file(var.create_web_server)
  tags = merge(
    {
      Name = format("prod-priv-i2")
    },
    var.prod_tags
  )
}
# priv-i3
resource "aws_instance" "prod-priv-i3" {
  ami                         = var.ami
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.prod-key1.key_name
  subnet_id                   = aws_subnet.prod-priv-az1-sub.id
  private_ip                  = "10.1.101.13"
  vpc_security_group_ids      = [aws_security_group.prod-priv-sg.id]
  depends_on                  = [aws_nat_gateway.prod-ngw]
  user_data                   = file(var.create_web_server)
  tags = merge(
    {
      Name = format("prod-priv-i3")
    },
    var.prod_tags
  )
}
# priv-i4
resource "aws_instance" "prod-priv-i4" {
  ami                         = var.ami
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.prod-key1.key_name
  subnet_id                   = aws_subnet.prod-priv-az1-sub.id
  private_ip                  = "10.1.101.14"
  vpc_security_group_ids      = [aws_security_group.prod-priv-sg.id]
  depends_on                  = [aws_nat_gateway.prod-ngw]
  user_data                   = file(var.create_web_server)
  tags = merge(
    {
      Name = format("prod-priv-i4")
    },
    var.prod_tags
  )
}
# priv-i5
resource "aws_instance" "prod-priv-i5" {
  ami                         = var.ami
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.prod-key1.key_name
  subnet_id                   = aws_subnet.prod-priv-az1-sub.id
  private_ip                  = "10.1.101.15"
  vpc_security_group_ids      = [aws_security_group.prod-priv-sg.id]
  depends_on                  = [aws_nat_gateway.prod-ngw]
  user_data                   = file(var.create_web_server)
  tags = merge(
    {
      Name = format("prod-priv-i5")
    },
    var.prod_tags
  )
}



########################################
# vpc dev
########################################
##### VPC
resource "aws_vpc" "dev" {
  cidr_block            = var.dev_cidr
  enable_dns_support    = true
  enable_dns_hostnames  = true
  tags = merge(
    {
      "Name" = format("dev")
    },
    var.dev_tags
  )
}

##### Subnets
resource "aws_subnet" "dev-pub-sub" {
  vpc_id            = aws_vpc.dev.id
  cidr_block        = var.dev_pub_cidr
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = merge(
    {
      Name = format("dev-pub-sub")
    },
    var.dev_tags
  )
}
resource "aws_subnet" "dev-priv-az1-sub" {
  vpc_id            = aws_vpc.dev.id
  cidr_block        = var.dev_priv_cidr_az1
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = merge(
    {
      Name = format("dev-priv-az1-sub")
    },
    var.dev_tags
  )
}
resource "aws_subnet" "dev-priv-az2-sub" {
  vpc_id            = aws_vpc.dev.id
  cidr_block        = var.dev_priv_cidr_az2
  availability_zone = data.aws_availability_zones.az.names[1]
  tags = merge(
    {
      Name = format("dev-priv-az2-sub")
    },
    var.dev_tags
  )
}
resource "aws_subnet" "dev-tgw-az1-sub" {
  vpc_id            = aws_vpc.dev.id
  cidr_block        = var.dev_tgw_cidr_az1
  availability_zone = data.aws_availability_zones.az.names[0]
  tags = merge(
    {
      Name = format("dev-tgw-az1-sub")
    },
    var.dev_tags
  )
}
resource "aws_subnet" "dev-tgw-az2-sub" {
  vpc_id            = aws_vpc.dev.id
  cidr_block        = var.dev_tgw_cidr_az2
  availability_zone = data.aws_availability_zones.az.names[1]
  tags = merge(
    {
      Name = format("dev-tgw-az2-sub")
    },
    var.dev_tags
  )
}

##### IGW
resource "aws_internet_gateway" "dev-igw" {
  vpc_id  = aws_vpc.dev.id
  tags = merge(
    {
      Name = format("dev-igw")
    },
    var.dev_tags
  )
}

##### NGW
resource "aws_eip" "dev-ngw-eip" {
  vpc = true
  tags = merge(
    {
      Name = format("dev-ngw-eip")
    },
    var.dev_tags
  )
}
resource "aws_nat_gateway" "dev-ngw" {
  allocation_id = aws_eip.dev-ngw-eip.id
  subnet_id     = aws_subnet.dev-pub-sub.id
  depends_on    = [aws_internet_gateway.dev-igw]
  tags = merge(
    {
      Name = format("dev-ngw")
    },
    var.dev_tags
  )
}

##### Route table
# pub route table
resource "aws_route_table" "dev-pub-rtb" {
  vpc_id  = aws_vpc.dev.id
  route {
    cidr_block = var.any_subnet
    gateway_id = aws_internet_gateway.dev-igw.id
  }
  tags = merge(
    {
      Name = format("dev-pub-rtb")
    },
    var.dev_tags
  )
}
resource "aws_route_table_association" "dev-pub-sub" {
  route_table_id = aws_route_table.dev-pub-rtb.id
  subnet_id      = aws_subnet.dev-pub-sub.id
}
# priv route table
resource "aws_route_table" "dev-priv-rtb" {
  vpc_id  = aws_vpc.dev.id
  route {
    cidr_block      = var.any_subnet
    nat_gateway_id  = aws_nat_gateway.dev-ngw.id
  }
  route {
    cidr_block          = var.prod_cidr
    transit_gateway_id  = aws_ec2_transit_gateway.tgw.id
  }
  tags = merge(
    {
      Name = format("dev-priv-rtb")
    },
    var.dev_tags
  )
}
resource "aws_route_table_association" "dev-priv-az1-sub" {
  route_table_id = aws_route_table.dev-priv-rtb.id
  subnet_id      = aws_subnet.dev-priv-az1-sub.id
}
resource "aws_route_table_association" "dev-priv-az2-sub" {
  route_table_id = aws_route_table.dev-priv-rtb.id
  subnet_id      = aws_subnet.dev-priv-az2-sub.id
}
resource "aws_route_table_association" "dev-tgw-az1-sub" {
  route_table_id = aws_route_table.dev-priv-rtb.id
  subnet_id      = aws_subnet.dev-tgw-az1-sub.id
}
resource "aws_route_table_association" "dev-tgw-az2-sub" {
  route_table_id = aws_route_table.dev-priv-rtb.id
  subnet_id      = aws_subnet.dev-tgw-az2-sub.id
}

##### NACL
resource "aws_network_acl" "dev-pub-nacl" {
  vpc_id = aws_vpc.dev.id
  subnet_ids = [
    aws_subnet.dev-pub-sub.id,
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
      Name = format("dev-pub-nacl")
    },
    var.dev_tags
  )
}
resource "aws_network_acl" "dev-priv-nacl" {
  vpc_id = aws_vpc.dev.id
  subnet_ids = [
    aws_subnet.dev-priv-az1-sub.id,
    aws_subnet.dev-priv-az2-sub.id,
  ]
  ingress {
    protocol   = "-1"
    rule_no    = 1
    action     = "deny"
    cidr_block = format("%s/32", aws_instance.prod-priv-i4.private_ip)
    from_port  = 0
    to_port    = 0
  }
  ingress {
    protocol   = "tcp"
    rule_no    = 10
    action     = "allow"
    cidr_block = format("%s/32", var.jump_host)
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
      Name = format("dev-priv-nacl")
    },
    var.dev_tags
  )
}
resource "aws_network_acl" "dev-tgw-nacl" {
  vpc_id = aws_vpc.dev.id
  subnet_ids = [
    aws_subnet.dev-tgw-az1-sub.id,
    aws_subnet.dev-tgw-az2-sub.id,
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
    rule_no    = 1
    action     = "deny"
    cidr_block = format("%s/32", aws_instance.dev-priv-i3.private_ip)
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
      Name = format("dev-tgw-nacl")
    },
    var.dev_tags
  )
}

##### Security Group
resource "aws_security_group" "dev-priv-sg" {
  vpc_id = aws_vpc.dev.id
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
    cidr_blocks = [var.rfc_1918_10, var.rfc_1918_172, var.rfc_1918_192]
    description = "HTTP Access"
  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.rfc_1918_10, var.rfc_1918_172, var.rfc_1918_192]
    description = "HTTPS Access"
  }
  ingress {
    from_port   = 8
    to_port     = 0
    protocol    = "icmp"
    cidr_blocks = [var.rfc_1918_10, var.rfc_1918_172, var.rfc_1918_192]
    description = "ICMP Access"
  }
  ingress {
    from_port   = 33434
    to_port     = 33534
    protocol    = "udp"
    cidr_blocks = [var.rfc_1918_10, var.rfc_1918_172, var.rfc_1918_192]
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
      Name = format("dev-priv-sg")
    },
    var.dev_tags
  )
}

##### SSH key pair
resource "aws_key_pair" "dev-key" {
  key_name    = format("dev-PubKey")
  public_key  = file(var.pub_key_path)
}

##### ec2 instances
# priv-i1
resource "aws_instance" "dev-priv-i1" {
  ami                         = var.ami
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.dev-key.key_name
  subnet_id                   = aws_subnet.dev-priv-az2-sub.id
  private_ip                  = "10.2.102.11"
  vpc_security_group_ids      = [aws_security_group.dev-priv-sg.id]
  depends_on                  = [aws_nat_gateway.dev-ngw]
  user_data                   = file(var.create_web_server)
  tags = merge(
    {
      Name = format("dev-priv-i1")
    },
    var.dev_tags
  )
}
# priv-i2
resource "aws_instance" "dev-priv-i2" {
  ami                         = var.ami
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.dev-key.key_name
  subnet_id                   = aws_subnet.dev-priv-az2-sub.id
  private_ip                  = "10.2.102.12"
  vpc_security_group_ids      = [aws_security_group.dev-priv-sg.id]
  depends_on                  = [aws_nat_gateway.dev-ngw]
  user_data                   = file(var.create_web_server)
  tags = merge(
    {
      Name = format("dev-priv-i2")
    },
    var.dev_tags
  )
}
# priv-i3
resource "aws_instance" "dev-priv-i3" {
  ami                         = var.ami
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.dev-key.key_name
  subnet_id                   = aws_subnet.dev-priv-az2-sub.id
  private_ip                  = "10.2.102.13"
  vpc_security_group_ids      = [aws_security_group.dev-priv-sg.id]
  depends_on                  = [aws_nat_gateway.dev-ngw]
  user_data                   = file(var.create_web_server)
  tags = merge(
    {
      Name = format("dev-priv-i3")
    },
    var.dev_tags
  )
}
# priv-i4
resource "aws_instance" "dev-priv-i4" {
  ami                         = var.ami
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.dev-key.key_name
  subnet_id                   = aws_subnet.dev-priv-az2-sub.id
  private_ip                  = "10.2.102.14"
  vpc_security_group_ids      = [aws_security_group.dev-priv-sg.id]
  depends_on                  = [aws_nat_gateway.dev-ngw]
  user_data                   = file(var.create_web_server)
  tags = merge(
    {
      Name = format("dev-priv-i4")
    },
    var.dev_tags
  )
}
# priv-i5
resource "aws_instance" "dev-priv-i5" {
  ami                         = var.ami
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.dev-key.key_name
  subnet_id                   = aws_subnet.dev-priv-az2-sub.id
  private_ip                  = "10.2.102.15"
  vpc_security_group_ids      = [aws_security_group.dev-priv-sg.id]
  depends_on                  = [aws_nat_gateway.dev-ngw]
  user_data                   = file(var.create_web_server)
  tags = merge(
    {
      Name = format("dev-priv-i5")
    },
    var.dev_tags
  )
}


########################################
# TGW
########################################
# TGW
resource "aws_ec2_transit_gateway" "tgw" {
  tags = merge(
    {
      Name = format("tgw")
    },
    var.dev_tags
  )
}
# vpc prod attachement
resource "aws_ec2_transit_gateway_vpc_attachment" "prod" {
  subnet_ids         = [
    aws_subnet.prod-tgw-az1-sub.id,
    aws_subnet.prod-tgw-az2-sub.id,
  ]
  transit_gateway_id = aws_ec2_transit_gateway.tgw.id
  vpc_id             = aws_vpc.prod.id
  tags = merge(
    {
      Name = format("prod")
    },
    var.dev_tags
  )
}
# vpc dev attachement
resource "aws_ec2_transit_gateway_vpc_attachment" "dev" {
  subnet_ids         = [
    aws_subnet.dev-tgw-az1-sub.id,
    aws_subnet.dev-tgw-az2-sub.id,
  ]
  transit_gateway_id = aws_ec2_transit_gateway.tgw.id
  vpc_id             = aws_vpc.dev.id
  tags = merge(
    {
      Name = format("dev")
    },
    var.dev_tags
  )
}
