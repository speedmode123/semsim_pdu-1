#!/bin/bash

# Run RS422 Integration Tests
# Requires SEMSIM to be running in emulator mode with RS422 enabled

echo "======================================================================"
echo "PDU RS422 Integration Tests"
echo "======================================================================"
echo ""
echo "PREREQUISITES:"
echo "  1. RS422 hardware connected to /dev/ttyUSB0"
echo "  2. SEMSIM running in emulator mode:"
echo "     python semsim.py --mode emulator --rs422-port /dev/ttyUSB0 --rs422-baud 115200"
echo ""
echo "======================================================================"
echo ""

# Check if RS422 port exists
if [ ! -e "/dev/ttyUSB0" ]; then
    echo "ERROR: RS422 port /dev/ttyUSB0 not found!"
    echo "Available ports:"
    ls /dev/ttyUSB* 2>/dev/null || echo "  No RS422 ports detected"
    echo ""
    echo "Please connect RS422 hardware or update TEST_PORT in test_rs422_integration.py"
    exit 1
fi

# Check port permissions
if [ ! -r "/dev/ttyUSB0" ] || [ ! -w "/dev/ttyUSB0" ]; then
    echo "WARNING: Insufficient permissions for /dev/ttyUSB0"
    echo "Run: sudo chmod 666 /dev/ttyUSB0"
    echo ""
fi

# Run tests
echo "Running RS422 integration tests..."
echo ""

python -m unittest tests.test_rs422_integration -v

echo ""
echo "======================================================================"
echo "RS422 Integration Tests Complete"
echo "======================================================================"
