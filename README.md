# PDU Simulator/Emulator

Power Distribution Unit (PDU) simulator and emulator for satellite systems.

## Features

- **Simulator Mode**: TCP/IP communication only, no hardware required
- **Emulator Mode**: Full hardware interface with RS422 and MCP23017 GPIO
- **State Management**: In-memory dataclasses (no database dependency)
- **CCSDS Protocol**: Space Packet protocol for TMTC
- **Dual PDU Support**: Nominal (0x65) and Redundant (0x66) units
- **Unit Line Control**: 71 power distribution lines controlled via MCP23017 GPIO expanders
- **Cross-Platform**: Simulator mode works on Windows, Linux, and macOS

## Installation

\`\`\`bash
# Install dependencies
pip install pyserial smbus2

# For emulator mode (hardware support - Linux/Raspberry Pi only)
pip install adafruit-circuitpython-mcp230xx

# Note: Emulator mode requires Linux with I2C/GPIO support
# Simulator mode works on all platforms (Windows, Linux, macOS)
\`\`\`

## Usage

### Simulator Mode (No Hardware)

\`\`\`bash
# Run with default settings
python semsim.py --mode simulator

# Custom TCP/IP settings
python semsim.py --mode simulator --tcp-ip 127.0.0.1 --tcp-port 5004
\`\`\`

### Emulator Mode (With Hardware)

\`\`\`bash
# Run with RS422 interface and MCP hardware
python semsim.py --mode emulator --rs422-port /dev/ttyUSB1

# Custom settings
python semsim.py --mode emulator \
    --tcp-ip 0.0.0.0 \
    --tcp-port 84 \
    --rs422-port /dev/ttyUSB1 \
    --rs422-baud 115200
\`\`\`

## Architecture

### State Management

The PDU state is managed using Python dataclasses in `pdu_state.py`:

- `PduHeartBeatState`: Heartbeat and state tracking
- `PduStatusState`: PDU status and error counters
- `PduUnitLineStatesState`: Power line enable/disable states
- `PduRawMeasurementsState`: Raw ADC measurements
- `PduConvertedMeasurementsState`: Converted measurements (currents, voltages)
- `PduStateManager`: Manages both nominal and redundant PDU units

### Command Processing

Commands are processed in `pdu.py`:

- `ObcHeartBeat`: Heartbeat exchange with OBC
- `GetPduStatus`: Get PDU status
- `PduGoOperate/Safe/Maintenance`: State transitions
- `SetUnitPwLines`: Enable power lines
- `GetUnitLineStates`: Read power line states
- `ResetUnitPwLines`: Reset power lines
- `OverwriteUnitPwLines`: Overwrite power line states
- `GetRawMeasurements`: Read raw ADC values
- `GetConvertedMeasurements`: Read converted measurements

### Communication

- **TCP/IP**: CCSDS Space Packet protocol (tmtc_manager.py)
- **RS422**: Serial interface for hardware communication (rs422_handler.py)
- **MCP23017**: GPIO expander for hardware control (mcp_manager.py)

### Hardware Control (Emulator Mode)

The MCP Manager (`mcp_manager.py`) controls 71 unit lines via 6 MCP23017 GPIO expanders:

- **MCP Addresses**: 0x27, 0x26, 0x25, 0x24, 0x23, 0x22
- **Unit Lines**: 0-70 mapped to specific MCP addresses and pins
- **Control Logic**: GPIO LOW = Unit Line ON, GPIO HIGH = Unit Line OFF
- **Monitoring**: Background thread monitors PDU state and updates hardware automatically

#### Unit Line Categories

- **High Power Heaters**: Lines 0-17 (18 lines)
- **Low Power Heaters**: Lines 18-39 (22 lines)
- **Avionic Loads**: Lines 40-41 (2 lines)
- **HDRM**: Lines 42-53 (12 lines)
- **Reaction Wheels**: Lines 54-57 (4 lines)
- **Propulsion**: Lines 58-59 (2 lines)
- **Isolated LDO**: Lines 60-65 (6 lines)
- **Isolated Power**: Lines 66-68 (3 lines)

## RS422 Communication

### RS422 Handler Architecture

The PDU emulator uses a dedicated `RS422Handler` class for serial communication:

**Key Features:**
- **Independent Thread**: RS422 operates on its own thread, parallel to TCP/IP
- **Frame-Based Protocol**: Uses custom packetization with start/end markers (0x55)
- **Binary Encoding**: Commands encoded using `pdu_packetization` C library
- **Bidirectional**: Sends and receives commands/responses asynchronously

**Communication Flow:**
1. OBC sends binary RS422 frame → PDU receives via serial port
2. PDU decodes frame → extracts message ID, logical unit ID, payload
3. PDU processes command using same `pdu.py` functions as TCP/IP
4. PDU encodes response → sends binary RS422 frame back to OBC

**Supported Commands via RS422:**
All ICD commands work identically via RS422 and TCP/IP:
- ObcHeartBeat, GetPduStatus, PduGoLoad/Safe/Operate
- SetUnitPwLines, ResetUnitPwLines, OverwriteUnitPwLines
- GetUnitLineStates, GetRawMeasurements, GetConvertedMeasurements

### Testing RS422

Since RS422 requires Linux hardware and the C packetization library, you can:

**Option 1: TCP/IP Testing (Recommended)**
\`\`\`bash
# Run simulator mode (works on all platforms)
python semsim.py --mode simulator --tcp-port 5004

# Run integration tests
python -m pytest tests/test_icd_integration.py -v
\`\`\`

**Option 2: RS422 Emulator Testing (Linux only)**
\`\`\`bash
# Terminal 1: Start emulator with RS422
python semsim.py --mode emulator --rs422-port /dev/ttyUSB1

# Terminal 2: Send RS422 commands from OBC hardware
# (Requires physical OBC or RS422 test equipment)
\`\`\`

**RS422 Frame Format:**
\`\`\`
[0x55][Message ID][Logical Unit ID][Payload Length][Payload...][0x55]
\`\`\`

## Testing

### Prerequisites

Before running tests, you must start the SEMSIM server in a separate terminal:

\`\`\`bash
# Terminal 1: Start SEMSIM server
python semsim.py --mode simulator --tcp-ip 127.0.0.1 --tcp-port 5004

# Wait for "TMTC Manager started" message
\`\`\`

Then run the tests:

\`\`\`bash
# Terminal 2: Run tests
bash run_tests.sh

# Or run directly
python -m unittest tests.test_icd_integration -v
\`\`\`

### ICD Integration Test

The `test_icd_integration.py` test suite validates complete OBC-to-SEMSIM communication:

- **TCP/IP Communication**: Sends CCSDS Space Packets via UDP to running SEMSIM server
- **ICD Compliance**: Verifies all responses match PDU Interface Control Document
- **Comprehensive Coverage**: Tests all major commands and state transitions

#### Test Cases

1. **OBC Heartbeat**: Heartbeat exchange with PDU
2. **Get PDU Status**: Status query and response validation
3. **Get Unit Line States**: Unit line state retrieval
4. **State Transitions**: PduGoOperate, PduGoSafe state changes
5. **Set Unit Power Lines**: Enable/disable power lines
6. **Get Converted Measurements**: ADC measurement retrieval
7. **Reset Unit Power Lines**: Reset specific power lines
8. **Multiple Commands Sequence**: Complex command sequences
9. **Invalid State Transitions**: Error handling validation

#### Running Tests

\`\`\`bash
# Start SEMSIM first (Terminal 1)
python semsim.py --mode simulator --tcp-ip 127.0.0.1 --tcp-port 5004

# Run tests (Terminal 2)
python -m unittest tests.test_icd_integration -v

# Run specific test
python -m unittest tests.test_icd_integration.TestPduIcdIntegration.test_01_heartbeat -v
\`\`\`

The test will:
1. Connect to the running SEMSIM server on `127.0.0.1:5004`
2. Execute all test cases
3. Validate ICD-compliant responses
4. Report results

**Note**: If SEMSIM is not running, the test will fail with a connection error message.

## PDU States

- **0**: Boot
- **1**: Load
- **2**: Operate
- **3**: Safe
- **4**: Maintenance

## APIDs

- **0x65**: Nominal PDU (0x100 in tests)
- **0x66**: Redundant PDU

## Logical Unit IDs

- **0**: High Power Heaters
- **1**: Low Power Heaters
- **2**: Reaction Wheels
- **3**: Propulsion
- **4**: Avionic Loads
- **5**: HDRM (Hold Down Release Mechanism)
- **6**: Isolated LDO
- **7**: Isolated Power
- **8**: Thermal and Flyback

## Development

### Project Structure

\`\`\`
pdu-simulator/
├── semsim.py              # Main entry point
├── pdu_state.py           # State management (dataclasses)
├── pdu.py                 # PDU commands and functions
├── tmtc_manager.py        # TMTC communication manager
├── rs422_handler.py       # RS422 serial interface
├── pdu_packetization.py   # PDU packet encoding/decoding
├── mcp.py                 # MCP23017 GPIO driver (low-level)
├── mcp_manager.py         # MCP hardware manager (high-level)
├── tests/
│   └── test_icd_integration.py  # ICD integration test
├── run_tests.sh           # Test runner script
└── README.md
\`\`\`

### Adding New Commands

1. Add command handler in `pdu.py`
2. Add command processing in `tmtc_manager.py` `cmd_processing()`
3. Add test case in `tests/test_icd_integration.py`

### Hardware Requirements (Emulator Mode)

- **Platform**: Linux or Raspberry Pi (I2C and GPIO support required)
- **Note**: Windows and macOS are not supported for emulator mode due to hardware limitations
- **Raspberry Pi** or compatible SBC with I2C support
- **6x MCP23017** GPIO expanders (addresses 0x22-0x27)
- **RS422 transceiver** connected to serial port
- **I2C bus** enabled and configured

## Troubleshooting

**Windows Compatibility**
- Simulator mode works on Windows without any hardware libraries
- If you see `NotImplementedError` from adafruit-blinka, you're trying to run emulator mode on Windows
- Solution: Use `--mode simulator` instead of `--mode emulator`
- For hardware testing, use Linux/Raspberry Pi

**MCP Hardware Not Found**
- Check I2C is enabled: `sudo raspi-config` → Interface Options → I2C
- Verify MCP addresses: `i2cdetect -y 1`
- Check wiring and power supply

**RS422 Communication Issues**
- Verify serial port: `ls /dev/ttyUSB*`
- Check baud rate matches OBC configuration
- Test with: `screen /dev/ttyUSB1 115200`

**State Not Updating**
- Check PDU is in OPERATE state (state 2)
- Verify commands are properly formatted CCSDS packets
- Enable debug logging in code

**Test Failures**
- Ensure no other process is using port 5004
- Check SEMSIM starts successfully (wait 3 seconds for initialization)
- Verify Python version is 3.7+ for proper subprocess handling

## License

[Your License Here]
