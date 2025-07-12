# Lab Facts

- This lab is created to understand how the packet traverse hop by hop when `TGW` is in the path in multi az environment.
- To confirm the packet path, we are blocking the packet at every hop using the `NACL(in/out)` from source to destination.
- We have 5 instances in both vpc that represents 5 below scenarios. We are testing each scenario using one pari, for example `prod-priv1 to dev-priv1`. First 4 scenario will be blocked while the 5th one will be a successful scenario without any `NACL` block.
  1. block `prod-priv1` to `dev-priv1` out at `prod-instance` subnet
  2. block `prod-priv2` to `dev-priv2` in at `prod-tgw` subnet
  3. block `prod-priv3` to `dev-priv3` out at `dev-tgw` subnet
  4. block `prod-priv4` to `dev-priv4` in at `dev-instance` subnet
  5. `prod-priv5` to `dev-priv5`, non-blocking scenario
- **Setup**
  - vpc prod
    - `az1 & az2` with `subnet1 & subnet2`
    - `instance 1 to 5` in `az1`
    - `az2` has no instance. It has only `tgw attachment`
  - vpc dev
    - `az1 & az2` with `subnet1 & subnet2`
    - `instance1 to 5` in `az2`
    - `az1` has no instance. It has only `tgw attachment`
  - jump subnet (for mgmt access to all instances in vpc)

**Note:** Take a look at `NACL Test` section of this doc https://docs.google.com/spreadsheets/d/1FUaSt125TKBG6dkf0uy4rXh3brT31PEa8ohWLdJxFHc/edit#gid=108573899
