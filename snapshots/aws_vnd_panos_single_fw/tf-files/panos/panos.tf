#################################### Configure PA FW ######################################
# vars
variable "username" {
  description = "The username to interact with the firewall"
}
variable "password" {
  description = "The password to interact with the firewall"
}
variable "mgmt_ip" {
  description = "mgmt ip of firewall"
}

# Define Provider
provider "panos" {
  hostname = var.mgmt_ip
  username = var.username
  password = var.password
}
data "panos_system_info" "config" {}

# Interface mgmt profile
# mgmt profile for data plan interfaces, allow only ping. SSH & HTTPS access should be enabled only on mgmt interface
resource "panos_management_profile" "allow_ping_dataplane_iface" {
  name = "allow_ping_dataplane_iface"
  ping = true
  permitted_ips = ["0.0.0.0/0"]
}
resource "panos_virtual_router" "vsys1" {
  name = "vsys1"
  interfaces = ["ethernet1/1", "ethernet1/2"]
  depends_on = [panos_ethernet_interface.e1]
}

# ethernet1/1 configuration
resource "panos_ethernet_interface" "e1" {
  name = "ethernet1/1"
  mode = "layer3"
  enable_dhcp = true
  create_dhcp_default_route = true
  management_profile = panos_management_profile.allow_ping_dataplane_iface.id
}
resource "panos_zone" "untrusted" {
  name = "untrusted"
  mode = "layer3"
 interfaces = [panos_ethernet_interface.e1.name]
}

# ethernet1/2 configuration
resource "panos_ethernet_interface" "e2" {
  name = "ethernet1/2"
  mode = "layer3"
  enable_dhcp = true
  management_profile = panos_management_profile.allow_ping_dataplane_iface.id
}
resource "panos_zone" "trusted" {
  name = "trusted"
  mode = "layer3"
  interfaces = [panos_ethernet_interface.e2.name]
}

# NAT Rules
resource "panos_nat_rule_group" "main" {
  rule {
    name = "Internet2Webserver"
    original_packet {
      source_zones = [panos_zone.untrusted.name]
      destination_zone = panos_zone.untrusted.name
      destination_interface = "any"
      source_addresses = ["any"]
      destination_addresses = ["10.1.1.10"]
      service = "service-http"
    }
    translated_packet {
      source {}
      destination {
        static_translation {
          address = "10.1.101.100"
        }
      }
    }
  }
  rule {
    name = "Private2Internet"
    original_packet {
      source_zones = [panos_zone.trusted.name]
      destination_zone = panos_zone.untrusted.name
      destination_interface = "any"
      source_addresses = ["any"]
      destination_addresses = ["any"]
    }
    translated_packet {
      source {
        dynamic_ip_and_port {
          translated_address{
            translated_addresses = ["10.1.1.10"]
          }
        }
      }
      destination {}
    }
  }
}

# Security Rules
resource "panos_security_rule_group" "main" {
  rule {
    name = "internet2web allow"
    source_zones = [panos_zone.untrusted.name]
    source_addresses = ["any"]
    source_users = ["any"]
    hip_profiles = ["any"]
    destination_zones = [panos_zone.trusted.name]
    destination_addresses = ["any"]
    applications = ["web-browsing"]
    services = ["application-default"]
    categories = ["any"]
    virus = "default"
    spyware = "default"
    vulnerability = "default"
    action = "allow"
  }
  rule {
    name = "web2internet allow"
    source_zones = [panos_zone.trusted.name]
    source_addresses = ["10.1.101.0/24"]
    source_users = ["any"]
    hip_profiles = ["any"]
    destination_zones = [panos_zone.untrusted.name]
    destination_addresses = ["any"]
    applications = ["any"]
    services = ["application-default"]
    categories = ["any"]
    virus = "default"
    spyware = "default"
    vulnerability = "default"
    action = "allow"
  }
}
