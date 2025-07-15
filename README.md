# Batfish Lab Validation Framework

The open source lab validation infrastructure that powers Batfish's empirical validation methodology, as described in ["Validating the Validator"](https://batfish.org/2020/12/18/validating-the-validator.html).

## Overview

This framework implements comprehensive multi-level benchmarking to validate Batfish network analysis accuracy against real device behavior. It provides the testing infrastructure that ensures Batfish models faithfully predict network device state across multiple vendors and complex network scenarios.

**Note**: This is an open-sourced subset of Intentionet's internal validation infrastructure. GitHub issues were automatically migrated during open sourcing and may contain outdated references. The lab creation and collection tooling has not yet been open sourced. Contributions and bug fixes are welcome!

## Validation Approach

**Multi-Level Benchmarking**: The framework implements three levels of validation as described in the Intentionet methodology:

- **Feature-Level**: Individual network features tested in isolation (route maps, ACLs, routing protocols)
- **Device-Level**: Complex feature interactions on single devices, testing vendor-specific behaviors
- **Network-Level**: Multi-device topologies validating end-to-end behaviors across vendors

**Empirical Testing**: 96 network labs with real device configurations and operational data capture, covering 12+ vendors including Arista EOS, Cisco IOS-XE/NX-OS, Juniper JunOS, and others.

**Continuous Validation**: Automated testing compares Batfish predictions against actual device state using sophisticated cost-based matching algorithms.

## Getting Started

### Requirements

- Python 3.10+
- Pybatfish
- Batfish server running locally (see [development setup instructions](https://github.com/batfish/batfish/tree/master/docs/development))

### Developer Setup

```bash
# Clone and set up environment
git clone https://github.com/batfish/lab-validation.git
cd lab-validation

# Recommended: Use a Python virtual environment.

# Install in development mode
pip install -e .
pip install -r requirements-dev.txt
```

### Running Lab Tests

```bash
# Run tests for a specific lab
pytest lab_tests/ --labname=eos_bgp_aggregate

# Run all lab validation tests
python run_all_labs.py

# Run all labs with filtering and options
python run_all_labs.py --lab-filter nxos --verbose --fail-fast

# Run tests with coverage
pytest --cov=lab_validation --cov-report=term-missing
```

### Example Lab Structure

Each lab in `snapshots/` contains:

- **configs/**: Device configuration files
- **show/**: Captured device show command outputs
- **validation/**: Expected failure definitions (sickbay.yaml)

## How It Works

The validation process implements the methodology described in the Intentionet blog post:

1. **Lab Environment**: Network configurations deployed in emulated environments
2. **Data Capture**: Device show commands capture actual operational state
3. **Batfish Analysis**: Network snapshot analyzed to predict device behavior
4. **Empirical Comparison**: Cost-based matching algorithms compare predicted vs. actual state
5. **Continuous Improvement**: Test failures tracked through GitHub issues drive model refinements

### Architecture Components

- **Multi-Vendor Validators**: 12+ vendor-specific implementations (Arista, Cisco, Juniper, etc.)
- **Sophisticated Parsers**: Vendor-specific command output parsing with complex grammar handling
- **Cost-Based Matching**: Advanced algorithms for pairing device data with Batfish predictions
- **Sickbay System**: Expected failure management with GitHub issue integration for model improvement tracking

## Development

### Testing Framework

```bash
# Run all tests (unit + lab integration)
pytest

# Run specific validator unit tests
pytest tests/test_arista_validator.py -v

# Run specific lab integration test
pytest lab_tests/test_labs.py --labname=eos_bgp_aggregate -v

# Code quality checks
pre-commit run --all-files
```

### Lab Coverage

The framework includes 96 network labs covering:

- **BGP**: Route aggregation, EVPN, multi-VRF scenarios
- **OSPF**: Multi-area, stub areas, route redistribution
- **Interfaces**: VLAN, VXLAN, port-channels, VRFs
- **Multi-vendor**: Cross-vendor interoperability testing
- **Data Center**: EVPN/VXLAN spine-leaf architectures

## Contributing

This framework provides the empirical foundation for Batfish's network modeling accuracy. Contributions help improve network analysis for the entire community.

1. Fork the repository
2. Create a feature branch
3. Add tests for any changes
4. Ensure all tests pass: `pytest && pre-commit run --all-files`
5. Submit a pull request

## Related Projects

- **[Batfish](https://github.com/batfish/batfish)**: Open source network configuration analysis engine
- **[Pybatfish](https://github.com/batfish/pybatfish)**: Python SDK for Batfish
- **[Intentionet Blog](https://batfish.org/2020/12/18/validating-the-validator.html)**: "Validating the Validator" methodology

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
