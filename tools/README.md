# Lab Bisection Tool

This directory contains tools for bisecting lab failures in Batfish to find when labs started failing.

## Tools

### `lab_bisect.py`

Main bisection tool that automatically tests different versions of Batfish to find the first commit that broke a lab.

**Usage:**

```bash
# Basic bisection - find when junos_as_path_acl started failing
python tools/lab_bisect.py --lab junos_as_path_acl --good-date 2022-09-01 --bad-date HEAD --verbose

# Test a specific commit without bisecting
python tools/lab_bisect.py --lab junos_as_path_acl --test-only HEAD --verbose

# Use specific commit hashes instead of dates
python tools/lab_bisect.py --lab junos_as_path_acl --good-commit abc123 --bad-commit def456

# Skip validation if you're sure about the range (saves time)
python tools/lab_bisect.py --lab junos_as_path_acl --good-date 2022-09-01 --bad-date HEAD --skip-validation
```

**Features:**

- **Smart range validation**: Tests good/bad commits first to catch invalid ranges early
- **Automatically manages Batfish server lifecycle** (start/stop/rebuild)
- **Cleans containers directory** to handle metadata changes
- **Uses git bisect** to efficiently find the first bad commit
- **Handles timeouts and errors gracefully**
- **Verbose logging** for debugging
- **Skip validation option** for trusted ranges to save time

**Requirements:**

- Batfish repository at `../batfish` (or specify with `--batfish-dir`)
- Python 3.7+ with subprocess support
- Git repository with commit history
- Ability to build and run Batfish server

### `test_lab_bisect.py`

Simple test script to verify the bisection tool works correctly.

```bash
python tools/test_lab_bisect.py
```

## Workflow

1. **Identify the failing lab**: Use pytest to confirm the lab is currently failing
2. **Determine good/bad timeframe**: Estimate when the lab was last known to pass
3. **Run bisection**: Use the tool to automatically find the first bad commit
4. **Analyze results**: Review the identified commit and its changes

## Example Workflow

```bash
# 1. Confirm current failure
pytest lab_tests/test_labs.py --labname=junos_as_path_acl -v

# 2. Run bisection (assuming lab passed in September 2022)
python tools/lab_bisect.py --lab junos_as_path_acl --good-date 2022-09-01 --bad-date HEAD --verbose

# 3. Review the identified commit
cd ../batfish
git show <first-bad-commit>
```

## How It Works

1. **Setup**: Validates paths and lab existence
2. **Commit Resolution**: Converts dates to commit hashes if needed
3. **Range Validation** (unless `--skip-validation`):
   - Tests the "good" commit to ensure it actually passes
   - Tests the "bad" commit to ensure it actually fails
   - Bails early if range is invalid (saves time!)
4. **Git Bisect**: Uses git bisect to efficiently navigate commit history
5. **For each commit**:
   - Checkout the commit in the Batfish repository
   - Clean containers directory (removes cached metadata)
   - Build and start Batfish server using `tools/bazel_run.sh`
   - Run the lab test using pytest
   - Mark commit as good/bad based on test result
   - Stop Batfish server
6. **Result**: Reports the first commit that broke the lab

## Troubleshooting

**Build failures**: Some commits may fail to build. The tool will skip these automatically.

**Server startup issues**: The tool waits up to 10 minutes for server build and startup, checking every 5 seconds if the server is responding on port 9996.

**Timeout issues**: Lab tests timeout after 5 minutes. Adjust for complex labs.

**Memory issues**: Batfish server uses up to 12GB RAM. Ensure sufficient memory.

**Port conflicts**: Batfish uses port 9996. Ensure it's available.

## Lab Failure Analysis

Once you find the first bad commit:

1. **Review commit changes**: Look at the diff to understand what changed
2. **Check related issues**: Look for GitHub issues related to the changes
3. **Test specific scenarios**: Run targeted tests to isolate the problem
4. **Update sickbay**: Add expected failures to `sickbay.yaml` if needed

## Notes

- The tool preserves your current git state in the lab-validation repository
- All git operations happen in the Batfish repository
- Server processes are cleaned up automatically, even on interruption
- Bisection state is reset automatically on completion or error
