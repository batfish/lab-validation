# associate ngw route table to the fs subnet
resource "aws_route_table_association" "rtb-asctn-ngw-fs-hr-west" {
  provider = aws.provider-2
  route_table_id = aws_route_table.rtb-ngw-hr-west.id
  subnet_id      = aws_subnet.subnet-fs-hr-west.id
}
