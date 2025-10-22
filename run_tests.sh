#!/bin/bash
# Run all PDU tests

echo "Running PDU Simulator Tests..."
echo "=============================="

# Run unit tests
echo ""
echo "Unit Tests - State Management"
python -m unittest tests.test_pdu_state -v

echo ""
echo "Unit Tests - PDU Commands"
python -m unittest tests.test_pdu_commands -v

echo ""
echo "Communication Tests"
python -m unittest tests.test_communication -v

echo ""
echo "=============================="
echo "All tests completed!"
