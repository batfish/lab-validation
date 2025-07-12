import json
import sys
from pathlib import Path
from typing import Text

from python_terraform import Terraform

USERNAME = "admin"
PASSWORD = "P@ssword"


def destroy_provider_aws(provider_aws: Text) -> None:
    """
    Destroy aws infrastructure using Terraform
    """
    tf_obj = get_tf_object(provider_aws)
    tf_destroy_aws(provider_aws, tf_obj)


def destroy_provider_panos(provider_panos: Text, mgmt_ip: Text) -> None:
    """
    Destroy panos device configuration using Terraform
    """
    tf_obj = get_tf_object(provider_panos)
    tf_destroy_panos(provider_panos, tf_obj, mgmt_ip)


def get_tf_object(provider_tf: Text) -> Terraform:
    """
    Creates Terraform object
    """
    path = Path.cwd().joinpath(provider_tf)
    return Terraform(working_dir=path)


def tf_destroy_aws(provider_aws: Text, tf_obj: Terraform) -> None:
    """
    Terraform destroy operation for aws provider
    """
    print(f"Destroying Provider {provider_aws}....")
    return_code, stdout, stderr = tf_obj.cmd(
        "destroy", auto_approve=True, capture_output=False
    )
    print(stdout)
    print(stderr, file=sys.stderr)
    if return_code != 0:
        raise Exception("TF Destroy failed")


def tf_destroy_panos(provider_panos: Text, tf_obj: Terraform, mgmt_ip: Text) -> None:
    """
    Terraform destroy operation for panos provider
    """
    print(f"Destroying Provider {provider_panos}....")
    provider_input = {"username": USERNAME, "password": PASSWORD, "mgmt_ip": mgmt_ip}
    return_code, stdout, stderr = tf_obj.cmd(
        "destroy", auto_approve=True, var=provider_input, capture_output=False
    )
    print(stdout)
    print(stderr, file=sys.stderr)
    if return_code != 0:
        raise Exception("TF Destroy failed")


def main():
    """
    Destroy panos provider
    """
    # Read mgmt ip from tfstate file
    terraform_tfstate = "aws/terraform.tfstate"
    with open(terraform_tfstate) as f:
        content = json.load(f)
    mgmt_ip = content["outputs"]["mgmt_ip_pub"]["value"]

    provider_panos = "panos"
    destroy_provider_panos(provider_panos, mgmt_ip)

    """
    Destroy panos provider
    """
    provider_aws = "aws"
    destroy_provider_aws(provider_aws)


if __name__ == "__main__":
    main()
