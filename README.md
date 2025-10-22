# PDU Simulator/Emulator

Power Distribution Unit (PDU) simulator and emulator for satellite systems.

## Features

- **Simulator Mode**: TCP/IP communication only, no hardware required
- **Emulator Mode**: Full hardware interface with RS422 and MCP23017 GPIO
- **State Management**: In-memory dataclasses (no database dependency)
- **CCSDS Protocol**: Space Packet protocol for TMTC
- **Dual PDU Support**: Nominal (0x65) and Redundant (0x66) units
- **Unit Line Control**: 71 power distribution lines controlled via MCP23017 GPIO expanders

## Installation

\`\`\`bash
# Install dependencies
pip install pyserial smbus2

# For emulator mode (hardware support)
pip install adafruit-circuitpython-mcp230xx
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
- **RS422**: Serial interface for hardware communication (rs422_interface.py)
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

## Testing

\`\`\`bash
# Run all tests
bash run_tests.sh

# Or run specific test suites
python -m unittest tests.test_pdu_state
python -m unittest tests.test_pdu_commands
python -m unittest tests.test_communication
python -m unittest tests.test_unit_lines
\`\`\`

### Test Coverage

- **test_pdu_state.py**: State management and dataclass functionality
- **test_pdu_commands.py**: PDU command processing and state transitions
- **test_communication.py**: Packet encoding/decoding and communication flow
- **test_unit_lines.py**: Unit line control and MCP hardware integration (with mocked hardware)

## PDU States

- **0**: Boot
- **1**: Load
- **2**: Operate
- **3**: Safe
- **4**: Maintenance

## APIDs

- **0x65**: Nominal PDU
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
├── rs422_interface.py     # RS422 serial interface
├── pdu_packetization.py   # PDU packet encoding/decoding
├── mcp.py                 # MCP23017 GPIO driver (low-level)
├── mcp_manager.py         # MCP hardware manager (high-level)
├── tests/
│   ├── test_pdu_state.py       # State management tests
│   ├── test_pdu_commands.py    # Command processing tests
│   ├── test_communication.py   # Communication tests
│   └── test_unit_lines.py      # Unit line and MCP tests
├── run_tests.sh           # Test runner script
└── README.md
\`\`\`

### Adding New Commands

1. Add command handler in `pdu.py`
2. Add command processing in `tmtc_manager.py` `cmd_processing()`
3. Add tests in `tests/test_pdu_commands.py`

### Hardware Requirements (Emulator Mode)

- **Raspberry Pi** or compatible SBC with I2C support
- **6x MCP23017** GPIO expanders (addresses 0x22-0x27)
- **RS422 transceiver** connected to serial port
- **I2C bus** enabled and configured

### Troubleshooting

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

## License

[Your License Here]
