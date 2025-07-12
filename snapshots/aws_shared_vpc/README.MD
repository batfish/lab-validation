##LAB Facts
Three different VPC(shared_services, dev & prod) owned by three different owners.
VPC `shared_services` will share one of it's subnet called `shared-subnet` where accounts `dev` & `prod` will spin up their resources.

####VPC breakup

- shared_services, account A
  - shared subnet
  - non shared subnet
- dev, account B
- prod, account C
- jump - this vpc is just to mgmt access for lab validation
