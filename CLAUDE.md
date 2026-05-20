# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -e .
pip install -r requirements-dev.txt
```

### Core Testing Commands

```bash
# Run all tests
pytest

# Run with coverage reporting
pytest --cov=lab_validation --cov-report=xml --cov-report=term-missing

# Run specific validator tests
pytest tests/test_arista_validator.py -v
pytest tests/test_nxos_validator.py -v

# Run specific lab integration test
pytest lab_tests/test_labs.py --labname=eos_bgp_aggregate -v

# Run single test method
pytest tests/test_arista_validator.py::TestAristaValidator::test_get_runtime_data -v
```

### Code Quality Commands

```bash
# Run pre-commit hooks (includes formatting, isort, prettier)
pre-commit run --all-files

# Type checking with mypy
mypy src/
```

## Architecture Overview

### Core Components

**Validation Framework**: Abstract `VendorValidator` base class with vendor-specific implementations. Each validator implements device data parsing, Batfish comparison, and specialized validation for interfaces, routing tables, BGP, and EVPN.

**Multi-Vendor Parsers**: Parsing systems in `src/lab_validation/parsers/` for each vendor (Arista EOS JSON, Cisco IOS-XE, NX-OS with EVPN support, JunOS, etc.) using grammar-based parsing and vendor-specific logic.

**Cost-Based Matching Algorithm**: Located in `src/lab_validation/utils/validation_utils.py`, implements pairing of device operational data against Batfish analysis results, handling next-hop analysis and route attribute comparison.

**Lab Test Framework**: Network labs in `snapshots/` directory, each containing device configurations, show command outputs, and optional validation rules. Labs follow consistent structure with `configs/`, `show/`, and `validation/` directories.

**Sickbay System**: Expected failure management using YAML files (`sickbay.yaml`) that reference GitHub issues for tracking known validation problems. Integrates with pytest to mark expected failures as `xfail`.

### Data Flow

1. **Lab Discovery**: Framework automatically discovers available labs from `snapshots/` directory
2. **Batfish Analysis**: Builds network snapshot and runs Batfish validation questions
3. **Device Data Parsing**: Vendor-specific parsers extract operational data from show commands
4. **Validation Engine**: Cost-based matching compares device state against Batfish predictions
5. **Result Processing**: Sickbay system handles expected failures and generates test report

## Code Structure

### Vendor Validators (`src/lab_validation/validators/`)

Each validator implements:

- `get_runtime_data()`: Parse device show command outputs
- `validate_interface_properties()`: Interface state validation
- `validate_main_rib_routes()`: Main routing table validation
- `validate_bgp_rib_routes()`: BGP table validation
- `validate_evpn_rib_routes()`: EVPN route validation (vendor-specific)

### Parser Architecture (`src/lab_validation/parsers/`)

- JSON parsing for modern APIs (Arista EOS)
- Text parsing with regex for traditional CLI (IOS, NX-OS)
- Structured parsing for complex outputs (JunOS, EVPN routes)

### Data Models (`src/lab_validation/models/`)

- `routes.py`: Route models with AS-path conversion and next-hop analysis
- `interface_properties.py`: Interface state models
- `runtime_data.py`: Node operational data structures

## Lab Data Structure

Each lab in `snapshots/` follows this pattern:

```
<lab_name>/
├── source/                   # Hand-authored build inputs (for labs built via lab_builder)
│   ├── topology.clab.yml    # Containerlab topology
│   ├── configs/             # Startup configs pushed to devices
│   ├── checks.yaml          # Lab-state preconditions
│   └── README.md            # Lab documentation and findings
├── configs/                  # Device configuration files (collected from running lab)
├── show/                     # Device show command outputs
│   └── host_nos.txt         # Device-to-vendor mapping
├── batfish/                  # Optional Batfish-specific inputs (e.g., layer1_topology.json)
└── validation/               # Optional validation rules
    └── sickbay.yaml         # Expected failure definitions with GitHub issues
```

`source/` keeps each lab self-contained: the hand-authored inputs sit
next to the collected outputs. Labs built via `lab_builder` (see
`infra/README.md`) put their topology/configs/checks here. Older labs
without `source/` were authored before the lab builder existed.

## Testing

### Unit Tests (`tests/`)

Parser and validator testing. Each vendor validator has test coverage for parsing logic and validation algorithms.

### Lab Integration Tests (`lab_tests/`)

End-to-end validation using real network lab data. Each lab runs independently with Batfish analysis, device data parsing, validation comparison, and sickbay handling.

Requires a running Batfish instance on localhost:9996.

### CI/CD Pipeline

GitHub Actions runs matrix strategy testing all labs in parallel, with Batfish JAR caching and coverage reporting.

## Coding Conventions

- **Python 3.10+** required (supports 3.10, 3.11, 3.12)
- **Pre-commit hooks** required for consistent code quality
- **Parser error handling**: parsers should crash (assert, KeyError) on
  unexpected data shapes rather than silently degrading with `.get()`
  defaults. Only use `.get()` when a key is genuinely optional per the
  schema.
- **Unit tests for parser changes**: any parser fix or extension must
  include a unit test covering the new code path.

## Lab Builder Infrastructure

See `infra/README.md` for detailed documentation on creating new labs
using containerlab on EC2.

## Project Configuration

- **Claude-facing documentation and project status should go in the
  working/ folder**. This is everything related to LLM-driven projects
  and tasks that does not face end users and contributors.
