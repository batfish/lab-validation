#################### common vars ####################
variable "profile" {
  description = "account profile"
  default     = "SandboxAdmin"
}
# change ssh pub key path as appropriate
variable "public-key-path" {
  description = "Public key path"
  default = "~/.ssh/id_rsa.pub"
}
variable "create-web-server" {
  description = "web server script"
  default = "./create-web-server.sh"
}
variable "update-server" {
  description = "update server and install nmap and nc"
  default = "./update-server.sh"
}

data "aws_caller_identity" "current" {}
