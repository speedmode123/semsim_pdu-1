"""
PDU Simulator/Emulator Main Entry Point
Unified script to run in simulator or emulator mode
"""
import argparse
import time
import logging
from threading import Thread
import signal
import sys

from pdu_state import PduStateManager
from tmtc_manager import tmtc_manager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)

# Global state manager
state_manager = None
mcp_manager = None
running = True


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global running
    LOGGER.info("Shutting down PDU simulator...")
    running = False
    sys.exit(0)


def run_simulator(tcp_ip: str, tcp_port: int):
    """Run PDU in simulator mode (TCP/IP only, no hardware)"""
    global state_manager, running
    
    LOGGER.info("=" * 60)
    LOGGER.info("PDU SIMULATOR MODE")
    LOGGER.info("=" * 60)
    LOGGER.info(f"TCP/IP Server: {tcp_ip}:{tcp_port}")
    LOGGER.info("Hardware interfaces: DISABLED")
    LOGGER.info("=" * 60)
    
    # Initialize state manager
    state_manager = PduStateManager()
    
    # Run TMTC manager
    try:
        while running:
            tmtc_manager(state_manager, tcp_ip, tcp_port, hardware_mode=False)
    except KeyboardInterrupt:
        LOGGER.info("Simulator stopped by user")
    except Exception as e:
        LOGGER.error(f"Simulator error: {e}")
        raise


def run_emulator(tcp_ip: str, tcp_port: int, rs422_port: str, rs422_baud: int):
    """Run PDU in emulator mode (TCP/IP + RS422 + MCP hardware)"""
    global state_manager, mcp_manager, running
    
    LOGGER.info("=" * 60)
    LOGGER.info("PDU EMULATOR MODE")
    LOGGER.info("=" * 60)
    LOGGER.info(f"TCP/IP Server: {tcp_ip}:{tcp_port}")
    LOGGER.info(f"RS422 Interface: {rs422_port} @ {rs422_baud} baud")
    LOGGER.info("Hardware interfaces: ENABLED (MCP23017, RS422)")
    LOGGER.info("=" * 60)
    
    # Initialize state manager
    state_manager = PduStateManager()
    
    try:
        from rs422_handler import RS422Handler
        rs422_available = True
    except ImportError as e:
        LOGGER.error(f"Failed to import RS422 handler: {e}")
        LOGGER.error("RS422 handler requires pdu_packetization C library")
        LOGGER.error("Please ensure the C library is available in the resource/ directory")
        rs422_available = False
    
    try:
        from mcp_manager import McpManager
    except ImportError as e:
        LOGGER.error(f"Failed to import MCP manager: {e}")
        LOGGER.error("MCP manager requires smbus2 and Linux platform")
        LOGGER.warning("Continuing without MCP hardware...")
        McpManager = None
    
    # Start MCP hardware manager
    if McpManager:
        try:
            mcp_manager = McpManager(state_manager, poll_interval=0.1)
            mcp_manager.start()
            LOGGER.info("MCP hardware manager started")
        except Exception as e:
            LOGGER.error(f"Failed to start MCP hardware manager: {e}")
            LOGGER.warning("Continuing without MCP hardware...")
            mcp_manager = None
    
    rs422_handler = None
    if rs422_available:
        try:
            rs422_handler = RS422Handler(rs422_port, rs422_baud, state_manager)
            if rs422_handler.start():
                LOGGER.info("RS422 handler started successfully")
            else:
                LOGGER.warning("Failed to start RS422 handler")
                rs422_handler = None
        except Exception as e:
            LOGGER.error(f"Failed to initialize RS422 handler: {e}")
            LOGGER.warning("Continuing without RS422...")
            rs422_handler = None
    
    # Run TMTC manager with hardware mode enabled
    try:
        while running:
            tmtc_manager(state_manager, tcp_ip, tcp_port, hardware_mode=True)
    except KeyboardInterrupt:
        LOGGER.info("Emulator stopped by user")
    except Exception as e:
        LOGGER.error(f"Emulator error: {e}")
        raise
    finally:
        if rs422_handler:
            rs422_handler.stop()
            LOGGER.info("RS422 handler shutdown complete")
        
        if mcp_manager:
            mcp_manager.shutdown()
            LOGGER.info("MCP hardware manager shutdown complete")


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description='PDU Simulator/Emulator for Satellite Power Distribution Unit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in simulator mode (no hardware)
  python semsim.py --mode simulator
  
  # Run in emulator mode with RS422
  python semsim.py --mode emulator --rs422-port /dev/ttyUSB1
  
  # Custom TCP/IP settings
  python semsim.py --mode simulator --tcp-ip 127.0.0.1 --tcp-port 5004
        """
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['simulator', 'emulator'],
        default='simulator',
        help='Run mode: simulator (TCP/IP only) or emulator (TCP/IP + RS422 + hardware)'
    )
    
    parser.add_argument(
        '--tcp-ip',
        type=str,
        default='0.0.0.0',
        help='TCP/IP address to bind (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--tcp-port',
        type=int,
        default=84,
        help='TCP/IP port to bind (default: 84)'
    )
    
    parser.add_argument(
        '--rs422-port',
        type=str,
        default='/dev/ttyUSB1',
        help='RS422 serial port (default: /dev/ttyUSB1)'
    )
    
    parser.add_argument(
        '--rs422-baud',
        type=int,
        default=115200,
        help='RS422 baud rate (default: 115200)'
    )
    
    args = parser.parse_args()
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run in selected mode
    if args.mode == 'simulator':
        run_simulator(args.tcp_ip, args.tcp_port)
    else:
        run_emulator(args.tcp_ip, args.tcp_port, args.rs422_port, args.rs422_baud)


if __name__ == "__main__":
    main()
