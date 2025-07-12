#! /bin/bash
sudo yum -y update
sudo yum -y install nmap
sudo yum -y install nc
sudo yum -y install httpd
sudo service httpd start
echo "<h1>Hello, Server is UP</h1>" | sudo tee /var/www/html/index.html
