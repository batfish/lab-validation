# Lab Facts

- This lab is created to understand how `instances` reaches to `vpc endpoint services` using different types of exit points i.e. IGW, NGW and VPC endpoints.
- **Setup**
  - single vpc `bat`
  - three different instance reaching to vpc endpoint services
    - `bat-pub01` via `igw`
    - `bat-nat01` via `ngw`
    - `bat-private01` via `vpc endpoint`
