"""
PDU State Management using Dataclasses
Replaces database-based state management with in-memory dataclasses
"""
from dataclasses import dataclass, field
from typing import List, Dict
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)


@dataclass
class PduHeartBeatState:
    """PDU Heartbeat state"""
    HeartBeat: int = 0
    PduState: int = 0

    def to_dict(self) -> dict:
        return {"PduHeartBeat": {"HeartBeat": self.HeartBeat, "PduState": self.PduState}}


@dataclass
class PduStatusState:
    """PDU Status state"""
    PduState: int = 0x01
    ProtectionStatus: int = 0x00
    CommHwStatus: int = 0x00
    CommSwStatus: int = 0x00
    UloadError: int = 0x00
    DloadError: int = 0x00
    CmdError: int = 0x00
    OperStatus: int = 0x00
    ConfigStatus: int = 0x00
    RequestAcceptedCount: int = 0x00
    RequestRejectedCount: int = 0x00
    BootType_ResetCode: int = 0x00

    def to_dict(self) -> dict:
        return {
            "PduStatus": {
                "PduState": self.PduState,
                "ProtectionStatus": self.ProtectionStatus,
                "CommHwStatus": self.CommHwStatus,
                "CommSwStatus": self.CommSwStatus,
                "UloadError": self.UloadError,
                "DloadError": self.DloadError,
                "CmdError": self.CmdError,
                "OperStatus": self.OperStatus,
                "ConfigStatus": self.ConfigStatus,
                "RequestAcceptedCount": self.RequestAcceptedCount,
                "RequestRejectedCount": self.RequestRejectedCount,
                "BootType_ResetCode": self.BootType_ResetCode
            }
        }


@dataclass
class PduUnitLineStatesState:
    """PDU Unit Line States"""
    HighPwHeaterEnSel: int = 0x00
    LowPwHeaterEnSel: int = 0x00
    ReactionWheelEnSel: int = 0x00
    PropEnSel: int = 0x00
    AvionicLoadEnSel: int = 0x00
    HdrmEnSel: int = 0x00
    IsolatedLdoEnSel: int = 0x00
    IsolatedPwEnSel: int = 0x00
    ThermAndFlybackEnSel: int = 0xFF

    def to_dict(self) -> dict:
        return {
            "PduUnitLineStates": {
                "HighPwHeaterEnSel": self.HighPwHeaterEnSel,
                "LowPwHeaterEnSel": self.LowPwHeaterEnSel,
                "ReactionWheelEnSel": self.ReactionWheelEnSel,
                "PropEnSel": self.PropEnSel,
                "AvionicLoadEnSel": self.AvionicLoadEnSel,
                "HdrmEnSel": self.HdrmEnSel,
                "IsolatedLdoEnSel": self.IsolatedLdoEnSel,
                "IsolatedPwEnSel": self.IsolatedPwEnSel,
                "ThermAndFlybackEnSel": self.ThermAndFlybackEnSel
            }
        }


@dataclass
class PduRawMeasurementsState:
    """PDU Raw Measurements"""
    HighPwHeaterAdcSel: List[int] = field(default_factory=lambda: [0x0000] * 9)
    LowPwHeaterAdcSel: List[int] = field(default_factory=lambda: [0x0000] * 4)
    ReactionWheelAdcSel: List[int] = field(default_factory=lambda: [0x0000] * 4)
    PropAdcSel: List[int] = field(default_factory=lambda: [0x0000] * 2)
    AvionicLoadAdcSel: List[int] = field(default_factory=lambda: [0x0000] * 2)
    HdrmAdcSel: List[int] = field(default_factory=lambda: [0x0000] * 16)
    IsolatedLdoAdcSel: List[int] = field(default_factory=lambda: [0xFFFF])
    IsolatedPwAdcSel: List[int] = field(default_factory=lambda: [0xFFFF])
    ThermAndFlybackAdcSel: List[int] = field(default_factory=lambda: [0x0000, 0x0000, 0x0000, 0x0000, 0x0000, 0xFFFF, 0xFFFF])

    def to_dict(self) -> dict:
        return {
            "PduRawMeasurements": {
                "HighPwHeaterAdcSel": self.HighPwHeaterAdcSel,
                "LowPwHeaterAdcSel": self.LowPwHeaterAdcSel,
                "ReactionWheelAdcSel": self.ReactionWheelAdcSel,
                "PropAdcSel": self.PropAdcSel,
                "AvionicLoadAdcSel": self.AvionicLoadAdcSel,
                "HdrmAdcSel": self.HdrmAdcSel,
                "IsolatedLdoAdcSel": self.IsolatedLdoAdcSel,
                "IsolatedPwAdcSel": self.IsolatedPwAdcSel,
                "ThermAndFlybackAdcSel": self.ThermAndFlybackAdcSel
            }
        }


@dataclass
class PduConvertedMeasurementsState:
    """PDU Converted Measurements"""
    HighPwHeaterAdcSel: List[float] = field(default_factory=lambda: [0.0] * 9)
    LowPwHeaterAdcSel: List[float] = field(default_factory=lambda: [0.0] * 4)
    ReactionWheelAdcSel: List[float] = field(default_factory=lambda: [0.0] * 4)
    PropAdcSel: List[float] = field(default_factory=lambda: [0.0] * 2)
    AvionicLoadAdcSel: List[float] = field(default_factory=lambda: [0.0] * 2)
    HdrmAdcSel: List[float] = field(default_factory=lambda: [0.0] * 16)
    IsolatedLdoAdcSel: List[int] = field(default_factory=lambda: [0xFFFF])
    IsolatedPwAdcSel: List[int] = field(default_factory=lambda: [0xFFFF])
    ThermAndFlybackAdcSel: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0, 0.0, 0xFFFF, 0xFFFF])

    def to_dict(self) -> dict:
        return {
            "PduConvertedMeasurements": {
                "HighPwHeaterAdcSel": self.HighPwHeaterAdcSel,
                "LowPwHeaterAdcSel": self.LowPwHeaterAdcSel,
                "ReactionWheelAdcSel": self.ReactionWheelAdcSel,
                "PropAdcSel": self.PropAdcSel,
                "AvionicLoadAdcSel": self.AvionicLoadAdcSel,
                "HdrmAdcSel": self.HdrmAdcSel,
                "IsolatedLdoAdcSel": self.IsolatedLdoAdcSel,
                "IsolatedPwAdcSel": self.IsolatedPwAdcSel,
                "ThermAndFlybackAdcSel": self.ThermAndFlybackAdcSel
            }
        }


@dataclass
class MsgAcknowledgementState:
    """Message Acknowledgement state"""
    RequestedMsgId: str = ""
    PduReturnCode: int = 0

    def to_dict(self) -> dict:
        return {
            "MsgAcknowledgement": {
                "RequestedMsgId": self.RequestedMsgId,
                "PduReturnCode": self.PduReturnCode
            }
        }


@dataclass
class AddrDloadStartState:
    """Address Download Start state"""
    PduDLoadLength: int = 0
    PduDLoadAddr: int = 0

    def to_dict(self) -> dict:
        return {
            "AddrDloadStart": {
                "PduDLoadLength": self.PduDLoadLength,
                "PduDLoadAddr": self.PduDLoadAddr
            }
        }


@dataclass
class AddrDloadDataState:
    """Address Download Data state"""
    PduDLoadData: int = 0

    def to_dict(self) -> dict:
        return {
            "AddrDloadData": {
                "PduDLoadData": self.PduDLoadData
            }
        }


@dataclass
class PduUnitState:
    """Complete state for a single PDU unit (nominal or redundant)"""
    heartbeat: PduHeartBeatState = field(default_factory=PduHeartBeatState)
    pdu_status: PduStatusState = field(default_factory=PduStatusState)
    unit_line_states: PduUnitLineStatesState = field(default_factory=PduUnitLineStatesState)
    raw_measurements: PduRawMeasurementsState = field(default_factory=PduRawMeasurementsState)
    converted_measurements: PduConvertedMeasurementsState = field(default_factory=PduConvertedMeasurementsState)
    msg_acknowledgement: MsgAcknowledgementState = field(default_factory=MsgAcknowledgementState)
    addr_dload_start: AddrDloadStartState = field(default_factory=AddrDloadStartState)
    addr_dload_data: AddrDloadDataState = field(default_factory=AddrDloadDataState)
    initialized: bool = False


class PduStateManager:
    """Manages state for both nominal and redundant PDU units"""
    
    def __init__(self):
        self.pdu_n = PduUnitState()
        self.pdu_r = PduUnitState()
        self._initialize_units()
    
    def _initialize_units(self):
        """Initialize both PDU units"""
        self.pdu_n.initialized = True
        self.pdu_r.initialized = True
        LOGGER.info("PDU state manager initialized with nominal and redundant units")
    
    def get_pdu_state(self, apid: int) -> PduUnitState:
        """Get PDU unit state by APID (0x65 for nominal, 0x66 for redundant)"""
        return self.pdu_n if apid == 0x65 else self.pdu_r
    
    def get_unit(self, apid: int) -> PduUnitState:
        """Get PDU unit by APID (0x65 for nominal, 0x66 for redundant)"""
        return self.pdu_n if apid == 0x65 else self.pdu_r
    
    def get_unit_by_name(self, unit_name: str) -> PduUnitState:
        """Get PDU unit by name ('pdu_n' or 'pdu_r')"""
        return self.pdu_n if unit_name == 'pdu_n' else self.pdu_r
    
    def read_state(self, unit_name: str, state_name: str) -> str:
        """Read state and return as JSON string (compatible with old db_manager interface)"""
        unit = self.get_unit_by_name(unit_name)
        
        state_map = {
            'PduHeartBeat': unit.heartbeat.to_dict(),
            'PduStatus': unit.pdu_status.to_dict(),
            'PduUnitLineStates': unit.unit_line_states.to_dict(),
            'PduRawMeasurements': unit.raw_measurements.to_dict(),
            'PduConvertedMeasurements': unit.converted_measurements.to_dict(),
            'MsgAcknowledgment': unit.msg_acknowledgement.to_dict(),
            'AddrDloadStart': unit.addr_dload_start.to_dict(),
            'AddrDloadData': unit.addr_dload_data.to_dict(),
            'STATE': unit.initialized
        }
        
        return json.dumps(state_map.get(state_name, {}))
    
    def update_state(self, unit_name: str, state_name: str, value: str):
        """Update state from JSON string (compatible with old db_manager interface)"""
        unit = self.get_unit_by_name(unit_name)
        
        try:
            data = json.loads(value)
            
            if state_name == 'PduHeartBeat' and 'PduHeartBeat' in data:
                unit.heartbeat.HeartBeat = data['PduHeartBeat']['HeartBeat']
                unit.heartbeat.PduState = data['PduHeartBeat']['PduState']
            elif state_name == 'PduStatus' and 'PduStatus' in data:
                status_data = data['PduStatus']
                for key, value in status_data.items():
                    setattr(unit.pdu_status, key, value)
            elif state_name == 'PduUnitLineStates' and 'PduUnitLineStates' in data:
                line_data = data['PduUnitLineStates']
                for key, value in line_data.items():
                    setattr(unit.unit_line_states, key, value)
            elif state_name == 'PduRawMeasurements' and 'PduRawMeasurements' in data:
                raw_data = data['PduRawMeasurements']
                for key, value in raw_data.items():
                    setattr(unit.raw_measurements, key, value)
            elif state_name == 'PduConvertedMeasurements' and 'PduConvertedMeasurements' in data:
                conv_data = data['PduConvertedMeasurements']
                for key, value in conv_data.items():
                    setattr(unit.converted_measurements, key, value)
            elif state_name == 'MsgAcknowledgment' and 'MsgAcknowledgment' in data:
                ack_data = data['MsgAcknowledgment']
                unit.msg_acknowledgement.RequestedMsgId = ack_data['RequestedMsgId']
                unit.msg_acknowledgement.PduReturnCode = ack_data['PduReturnCode']
            elif state_name == 'STATE':
                unit.initialized = bool(int(value))
                
        except (json.JSONDecodeError, KeyError) as e:
            LOGGER.error(f"Error updating state {state_name} for {unit_name}: {e}")
