import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Text

import netmiko
from netmiko import Netmiko
from python_terraform import Terraform

USERNAME = "admin"
PASSWORD = "P@ssword"


def deploy_provider_aws(provider_aws: Text) -> None:
    """
    Deploy aws infrastructure using Terraform. It performs Terraform init and apply operation.
    """
    tf_obj = get_tf_object(provider_aws)
    tf_init(tf_obj)
    tf_apply_aws(provider_aws, tf_obj)


def deploy_provider_panos(provider_aws: Text, mgmt_ip: Text) -> None:
    """
    Configure panos device using Terraform. It performs Terraform init and apply operation.
    """
    tf_obj = get_tf_object(provider_aws)
    tf_init(tf_obj)
    tf_apply_panos(provider_aws, tf_obj, mgmt_ip)


def get_tf_object(provider_tf: Text) -> Terraform:
    """
    Creates Terraform object
    """
    path = Path.cwd().joinpath(provider_tf)
    return Terraform(working_dir=path)


def tf_init(tf_obj: Terraform) -> None:
    """
    Performs Terraform provider initialization
    """
    return_code, stdout, stderr = tf_obj.cmd("init")
    print(stderr, file=sys.stderr)
    if return_code != 0:
        raise Exception("TF apply failed")


def tf_apply_aws(provider_aws: Text, tf_obj: Terraform) -> None:
    """
    Terraform apply operation for aws provider
    """
    print(f"Applying Provider {provider_aws}....")
    return_code, stdout, stderr = tf_obj.cmd(
        "apply", auto_approve=True, capture_output=False
    )
    print(stdout)
    print(stderr, file=sys.stderr)
    if return_code != 0:
        raise Exception("TF apply failed")


def tf_apply_panos(provider_panos: Text, tf_obj: Terraform, mgmt_ip: Text) -> None:
    """
    Terraform apply operation for panos provider
    """
    print(f"Applying Provider {provider_panos}....")
    provider_input = {"username": USERNAME, "password": PASSWORD, "mgmt_ip": mgmt_ip}
    return_code, stdout, stderr = tf_obj.cmd(
        "apply", auto_approve=True, var=provider_input, capture_output=False
    )
    print(stdout)
    print(stderr, file=sys.stderr)
    if return_code != 0:
        raise Exception("TF apply failed")


def wait_for_fw(device_args: Dict) -> Netmiko:
    """
    Make SSH connection to device using netmiko and wait until fw comes online
    """
    print("Checking fw status...")
    while True:
        try:
            netmiko_obj = Netmiko(**device_args)
            output = netmiko_obj.config_mode()
            if output:
                print("fw is up now...")
                break
        # Exception needed to handle fw initialization
        except (netmiko.ssh_exception.SSHException, OSError, ValueError) as e:
            print("fw is not ready yet ...")
            print(f"{e.__class__.__name__}: {e}")
            time.sleep(5)
    return netmiko_obj


def run_commands(device: Netmiko, commands: List) -> None:
    """
    Run commands using netmiko
    """
    output = device.send_config_set(commands, cmd_verify=False)
    print(output)


def main():
    """
    Run the aws provider which will do the following tasks
    - init terraform
    - deploy aws infrastructure
    - create firewall instance
    - wait for FW instance to come up
    - set initial/first-time fw password
    """
    provider_aws = "aws"
    deploy_provider_aws(provider_aws)

    # Read mgmt ip from tfstate file
    terraform_tfstate = "aws/terraform.tfstate"
    with open(terraform_tfstate) as f:
        content = json.load(f)
    mgmt_ip = content["outputs"]["mgmt_ip_pub"]["value"]

    device_args = {
        "device_type": "paloalto_panos",
        "host": mgmt_ip,
        "username": USERNAME,
        "use_keys": True,
        "allow_agent": True,
        "global_delay_factor": 3,
    }

    # wait for fw to come up
    device = wait_for_fw(device_args)

    # set initial/first time password
    commands = [
        f"set mgt-config users {USERNAME} password",
        PASSWORD,
        PASSWORD,
        "commit",
    ]
    run_commands(device, commands)

    """
    Run the panos provider which will do the following tasks
    - init terraform
    - configure firewall instance
    """
    provider_panos = "panos"
    deploy_provider_panos(provider_panos, mgmt_ip)

    # commit changes
    commands = ["commit"]
    run_commands(device, commands)


if __name__ == "__main__":
    main()
