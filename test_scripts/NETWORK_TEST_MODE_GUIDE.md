# Network Manager Test Mode Guide

## Overview
The Network Manager Test Mode provides special commands and features for automated testing and debugging of the network switching logic. When enabled, it adds test commands accessible through the CLI interface.

## Enabling Test Mode

### Compilation
To enable test mode, compile with the `NETWORK_TEST_MODE` flag:

```bash
# Using CMake
cmake -DNETWORK_TEST_MODE=1 ..
make

# Using direct compilation
gcc -DNETWORK_TEST_MODE=1 -DLINUX_PLATFORM ... process_network.c
```

### Runtime Environment
Set the environment variable before running:
```bash
export NETWORK_TEST_MODE=1
./your_application
```

## Test Commands

All test commands start with `test` prefix. Available commands:

### 1. Force Interface Failure
```
test force_fail <interface>
```
- Forces the specified interface to fail (score=0, latency=9999)
- Starts a 30-second cooldown period
- Example: `test force_fail eth0`

### 2. Clear All Failures
```
test clear_failures
```
- Removes all cooldown periods
- Allows immediate retry of all interfaces

### 3. Show Detailed State
```
test show_state
```
- Displays current state machine state
- Shows all interface statuses
- Shows hysteresis information

### 4. Force DNS Refresh
```
test dns_refresh
```
- Clears the DNS cache
- Forces re-resolution on next ping

### 5. Reset Hysteresis
```
test hysteresis_reset
```
- Clears hysteresis active state
- Resets interface switch counter

### 6. Set Interface Score
```
test set_score <interface> <score>
```
- Manually sets an interface's score (0-10)
- Example: `test set_score wlan0 8`

## Test Scenarios

### 1. Interface Failover Test
```bash
# Start with eth0 as primary
net

# Force eth0 failure
test force_fail eth0

# Verify switch to wlan0
net

# Clear failures and verify recovery
test clear_failures
```

### 2. Hysteresis Test
```bash
# Rapidly switch interfaces
net eth0 down
net eth0 up
net eth0 down
net eth0 up
net eth0 down
net eth0 up

# Check if hysteresis is active
net
test show_state
```

### 3. State Machine Test
```bash
# Force all interfaces down
test force_fail eth0
test force_fail wlan0
test force_fail ppp0

# Check state (should be NET_INIT)
test show_state

# Clear one interface and verify state transition
test clear_failures
```

### 4. DNS Cache Test
```bash
# Check current DNS cache
net

# Force refresh
test dns_refresh

# Verify new resolution
net
```

## Automated Testing

### Using the PTY Controller

The PTY controller (`pty_test_controller.py`) can automate these tests:

```python
# Basic test execution
./pty_test_controller.py /path/to/app --tests all

# With logging
./pty_test_controller.py /path/to/app --log test.log --json results.json
```

### Writing Custom Tests

Add test cases to the PTY controller:

```python
def test_custom_scenario(controller):
    # Force primary interface failure
    controller.run_test("Force ETH0 Fail", "test force_fail eth0")
    
    # Wait for failover
    time.sleep(5)
    
    # Verify failover occurred
    controller.run_test("Check Failover", "net", "wlan0")
    
    # Test recovery
    controller.run_test("Clear Failures", "test clear_failures")
```

## Integration with CI/CD

### Environment Setup
```yaml
# Example GitHub Actions
env:
  NETWORK_TEST_MODE: 1
  NETMGR_ETH0_COOLDOWN_MS: 5000  # Faster for testing
  NETMGR_HYSTERESIS_ENABLED: 1
```

### Test Script
```bash
#!/bin/bash
# ci_test.sh

# Build with test mode
cmake -DNETWORK_TEST_MODE=1 ..
make

# Run automated tests
python3 pty_test_controller.py ./app --json test_results.json

# Check results
if [ $? -eq 0 ]; then
    echo "All tests passed"
else
    echo "Tests failed"
    cat test_results.json
    exit 1
fi
```

## Best Practices

1. **Always clear failures** after tests to avoid affecting subsequent tests
2. **Use reasonable delays** between commands to allow state transitions
3. **Check both state and output** to verify behavior
4. **Use hysteresis reset** between test scenarios
5. **Monitor logs** for detailed state machine transitions

## Troubleshooting

### Test Commands Not Working
- Verify `NETWORK_TEST_MODE` was defined during compilation
- Check that you're using the correct command syntax
- Look for `[TEST]` prefixes in log output

### Unexpected Behavior
- Use `test show_state` to see internal state
- Check if hysteresis is blocking switches
- Verify no interfaces are in cooldown

### Timing Issues
- Adjust timing constants via environment variables
- Use longer delays in automated tests
- Consider network initialization time

## Example Test Suite

```bash
#!/bin/bash
# Full test suite example

echo "=== Network Manager Test Suite ==="

# Test 1: Basic failover
echo "Test 1: Basic Failover"
echo "test force_fail eth0" | nc -q 1 localhost 23
sleep 5
echo "net" | nc -q 1 localhost 23

# Test 2: Hysteresis
echo "Test 2: Hysteresis"
for i in {1..5}; do
    echo "net eth0 down" | nc -q 1 localhost 23
    sleep 0.5
    echo "net eth0 up" | nc -q 1 localhost 23
    sleep 0.5
done
echo "test show_state" | nc -q 1 localhost 23

# Test 3: Recovery
echo "Test 3: Recovery"
echo "test clear_failures" | nc -q 1 localhost 23
sleep 10
echo "net" | nc -q 1 localhost 23

echo "=== Test Suite Complete ==="
```