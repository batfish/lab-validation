#!/bin/bash
set -euo pipefail

sudo yum update -y
sudo yum install nmap nc -y
