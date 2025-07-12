#!/bin/bash
set -euo pipefail

sudo yum update -y
sudo yum install nmap nc httpd -y
sudo systemctl start httpd
echo "<h1>Hello, Server is UP</h1>" | sudo tee /var/www/html/index.html
