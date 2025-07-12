##### regions
variable "vpc_region_west" {
  description = "VPC Region"
  default     = "us-west-1"
}

##### profiles
variable "profile-hr" {
  default     = "SandboxAdmin"
}

#### providers
provider "aws" {
  alias = "hr"
  profile = var.profile-hr
  region  = var.vpc_region_west
}
data "aws_caller_identity" "hr" {
    provider = aws.hr
}

##### change ssh pub key path as appropriate
variable "public_key_path" {
  description = "Public key path"
  default = "~/.ssh/id_rsa.pub"
}
resource "aws_key_pair" "ssh-key-hr" {
  provider = aws.hr
  key_name = "publicKey"
  public_key = file(var.public_key_path)
}

##### instance type
variable "ec2-instance-type" {
  description = "type for aws EC2 instance"
  default     = "t2.micro"
}
variable "ec2-instance-ami-west" {
  description = "AMI for aws EC2 instance"
  default     = "ami-09a7fe78668f1e2c0"
}

##### script to configure instances ######
variable "create-web-server" {
  description = "web server script"
  default = "./create-web-server.sh"
}
variable "update-server" {
  description = "update server and install nmap and nc"
  default = "./update-server.sh"
}



 ##### variables
variable "cidr-hr-west" {
  default     = "10.3.0.0/16"
}
variable "cidr-public-hr-west" {
  default     = "10.3.1.0/24"
}
variable "cidr-private-hr-west" {
  default     = "10.3.101.0/24"
}

#### AZ data source
data "aws_availability_zones" "az-hr" {
  provider = aws.hr
  state = "available"
}

##### Define VPC
resource "aws_vpc" "vpc-hr-west" {
  provider = aws.hr
  cidr_block = var.cidr-hr-west
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = "vpc-hr-west"
  }
}

#################### subnet ####################
# Define public subnet
resource "aws_subnet" "public-hr-west" {
  provider = aws.hr
  vpc_id     = aws_vpc.vpc-hr-west.id
  cidr_block = var.cidr-public-hr-west
  availability_zone = data.aws_availability_zones.az-hr.names[0]
  tags = {
    Name = format("public-hr-west")
  }
}
# Define private subnet
resource "aws_subnet" "private-hr-west" {
  provider = aws.hr
  vpc_id     = aws_vpc.vpc-hr-west.id
  cidr_block = var.cidr-private-hr-west
  availability_zone = data.aws_availability_zones.az-hr.names[0]
  tags = {
    Name = format("private-hr-west")
  }
}

#################### igw-ngw ####################
# Define igw
resource "aws_internet_gateway" "igw-hr-west" {
  provider = aws.hr
  vpc_id = aws_vpc.vpc-hr-west.id
  tags = {
    Name = format("igw-hr-west")
  }
}
# Define elastic ip for ngw
resource "aws_eip" "eip-ngw-hr-west" {
  provider = aws.hr
  vpc = true
    tags = {
    Name = format("eip-ngw-hr-west")
  }
}
# Define ngw
resource "aws_nat_gateway" "ngw-hr-west" {
  provider = aws.hr
  allocation_id = aws_eip.eip-ngw-hr-west.id
  subnet_id     = aws_subnet.public-hr-west.id
  depends_on = [aws_internet_gateway.igw-hr-west]
    tags = {
    Name = format("ngw-hr-west")
  }
}

#################### route tables ####################
# Define route table  - igw
resource "aws_route_table" "rtb-igw-hr-west" {
  provider = aws.hr
  vpc_id = aws_vpc.vpc-hr-west.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw-hr-west.id
  }
  tags = {
    Name = format("rtb-igw-hr-west")
  }
}
# associate igw route table to the public subnet
resource "aws_route_table_association" "rtb-asctn-igw-public-hr-west" {
  provider = aws.hr
  route_table_id = aws_route_table.rtb-igw-hr-west.id
  subnet_id      = aws_subnet.public-hr-west.id
}

# Define route table  - ngw
resource "aws_route_table" "rtb-ngw-hr-west" {
  provider = aws.hr
  vpc_id = aws_vpc.vpc-hr-west.id
  route {
    cidr_block = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.ngw-hr-west.id
  }
  tags = {
    Name = format("rtb-ngw-hr-west")
  }
}
# associate ngw route table to the private subnet
resource "aws_route_table_association" "rtb-asctn-ngw-private-hr-west" {
  provider = aws.hr
  route_table_id = aws_route_table.rtb-ngw-hr-west.id
  subnet_id      = aws_subnet.private-hr-west.id
}

#default route table
resource "aws_default_route_table" "rtb-default" {
  provider = aws.hr
  default_route_table_id = aws_vpc.vpc-hr-west.default_route_table_id
  route {
    cidr_block = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.ngw-hr-west.id
  }
}

#################### instances ####################
# Create EC2 linux instance - public
resource "aws_instance" "public-vpc-hr-west" {
  provider = aws.hr
  count = 1
  ami = var.ec2-instance-ami-west
  instance_type = var.ec2-instance-type
  key_name = aws_key_pair.ssh-key-hr.key_name
  subnet_id = aws_subnet.public-hr-west.id
  private_ip = "10.3.1.100"
  associate_public_ip_address = "true"
  vpc_security_group_ids = [aws_security_group.sg-hr-west.id]
  depends_on = [aws_internet_gateway.igw-hr-west]
  user_data = file(var.create-web-server)
  tags = {
    Name =  format("public%s-hr-west", count.index+1)
  }
}

# Create EC2 linux instance - private
resource "aws_instance" "private-vpc-hr-west" {
  provider = aws.hr
  count = 1
  ami = var.ec2-instance-ami-west
  instance_type = var.ec2-instance-type
  key_name = aws_key_pair.ssh-key-hr.key_name
  subnet_id = aws_subnet.private-hr-west.id
  private_ip = "10.3.101.100"
  associate_public_ip_address = "true"
  vpc_security_group_ids = [aws_security_group.sg-hr-west.id]
  depends_on = [aws_nat_gateway.ngw-hr-west]
  user_data = file(var.create-web-server)
  tags = {
    Name =  format("private%s-hr-west", count.index+1)
  }
}

# Define security-group
resource "aws_security_group" "sg-hr-west" {
  provider = aws.hr
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
      cidr_blocks = ["0.0.0.0/0"]
      description = "ICMP Access"
  }
 egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all"
  }
  tags = {
    Name = format("sg-hr-west")
  }
}
##### NACLs
resource "aws_network_acl" "nacl-hr-west" {
  provider = aws.hr
  vpc_id = aws_vpc.vpc-hr-west.id
  subnet_ids = [
    aws_subnet.public-hr-west.id,
    aws_subnet.private-hr-west.id
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
    Name = format("nacl-hr-west")
  }
}
