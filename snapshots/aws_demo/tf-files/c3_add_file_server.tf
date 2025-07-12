variable "subnet-fs-hr-west" {
  description = "subnet file server"
  default     = "10.3.102.0/24"
}

# Define fs subnet
resource "aws_subnet" "subnet-fs-hr-west" {
  provider = aws.provider-2
  vpc_id     = aws_vpc.vpc-hr-west.id
  cidr_block = var.subnet-fs-hr-west
  tags = {
    Name = format("subnet-fs-hr-west")
  }
}

# Define security-group fs
resource "aws_security_group" "sg-fs-hr-west" {
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
    Name = format("sg-fs-hr-west")
  }
}

# Create EC2 linux instance - fs
resource "aws_instance" "fs-vpc-hr-west" {
  provider = aws.provider-2
  count = 1
  ami = var.california-ec2-instance-ami
  instance_type = var.california-ec2-instance-type
  key_name = aws_key_pair.provider-2-ec2key.key_name
  subnet_id = aws_subnet.subnet-fs-hr-west.id
  vpc_security_group_ids = [aws_security_group.sg-fs-hr-west.id]
  depends_on = [aws_nat_gateway.ngw-hr-west]
  user_data = file(var.update-server)
  tags = {
    Name =  format("fs%s-hr-west", count.index+1)
  }
}
