"""
PDU Functions and Commands
Refactored to use PduStateManager instead of db_manager
"""
import logging
import json
import random
import struct

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)

PduState = {
    "PduGoBoot": 0,
    "PduGoLoad": 1,
    "PduGoOperate": 2,
    "PduGoSafe": 3,
    "PduGoMaintenance": 4
}

LogicalUnitId = {
    0: "HighPwHeaterEnSel",
    1: "LowPwHeaterEnSel",
    2: "ReactionWheelEnSel",
    3: "PropEnSel",
    4: "AvionicLoadEnSel",
    5: "HdrmEnSel",
    6: "IsolatedLdoEnSel",
    7: "IsolatedPwEnSel",
    8: "ThermAndFlybackEnSel"
}


def GetMsgAcknowledgement(j_command_packet, apid, state_manager):
    """Generate message acknowledgement"""
    unit = state_manager.get_unit(apid)
    
    LOGGER.info(f"j_command_packet: {j_command_packet}")
    for cmd, param_list in j_command_packet.items():
        unit.msg_acknowledgement.RequestedMsgId = cmd
        
        if "PduGoOperate" in str(cmd):
            if unit.pdu_status.PduState in [1, 4]:
                unit.msg_acknowledgement.PduReturnCode = 0
            else:
                unit.msg_acknowledgement.PduReturnCode = 1
                
        elif "PduGoSafe" in str(cmd):
            if unit.pdu_status.PduState == 2:
                unit.msg_acknowledgement.PduReturnCode = 0
            else:
                unit.msg_acknowledgement.PduReturnCode = 1
                
        elif "PduGoMaintenance" in str(cmd):
            if unit.pdu_status.PduState in [2, 3]:
                unit.msg_acknowledgement.PduReturnCode = 0
            else:
                unit.msg_acknowledgement.PduReturnCode = 1
        
        TYPE = 1
        SUBTYPE = 7 if unit.msg_acknowledgement.PduReturnCode == 0 else 8
    
    return unit.msg_acknowledgement.to_dict(), TYPE, SUBTYPE


def ObcHeartBeat(ObcHeartBeat, apid, state_manager):
    """Handle OBC heartbeat"""
    unit = state_manager.get_unit(apid)
    
    updated_status = unit.pdu_status.PduState
    LOGGER.info(f"PDU internal updated_status {updated_status}")
    
    updated_heartbeat = unit.heartbeat.HeartBeat
    LOGGER.info(f"PDU updated_heartbeat {updated_heartbeat}")
    
    unit.heartbeat.HeartBeat = ObcHeartBeat["ObcHeartBeat"]["HeartBeat"]
    unit.heartbeat.PduState = updated_status
    LOGGER.info(f"Dict_PduHeartBeat: {unit.heartbeat.to_dict()}")
    
    return json.dumps(unit.heartbeat.to_dict())


def GetPduStatus(GetPduStatus, apid, state_manager):
    """Get PDU status"""
    unit = state_manager.get_unit(apid)
    return json.dumps(unit.pdu_status.to_dict())


def GetUnitLineStates(GetUnitLineStates, apid, state_manager):
    """Get unit line states"""
    unit = state_manager.get_unit(apid)
    return json.dumps(unit.unit_line_states.to_dict())


def SetUnitPwLines(SetUnitPwLines, apid, state_manager):
    """Set unit power lines"""
    unit = state_manager.get_unit(apid)
    
    LogicalUnitIdn = LogicalUnitId[SetUnitPwLines["SetUnitPwLines"]["LogicUnitId"]]
    LOGGER.info(f"LogicalUnitId: {LogicalUnitIdn}")
    
    NewItem_SetUnitPwLines = SetUnitPwLines["SetUnitPwLines"]["Parameters"]
    setattr(unit.unit_line_states, LogicalUnitIdn, NewItem_SetUnitPwLines)
    
    # Update measurements based on line states
    status = NewItem_SetUnitPwLines
    converted_values = []
    
    if LogicalUnitIdn == "HighPwHeaterEnSel":
        nb_lines = 18
        nb_adc = 9
        bin_status = f"{status:0{nb_lines}b}"[::-1]
        
        for idx_adc in range(nb_adc):
            htr_states = bin_status[2*idx_adc:2*idx_adc+2]
            adc_val = random.uniform(-0.01, 0.01)
            for state in htr_states:
                if state == '1':
                    adc_val += random.uniform(7.4/2-0.01, 7.4/2+0.01)
            converted_values.append(adc_val)
    
    elif LogicalUnitIdn == "LowPwHeaterEnSel":
        nb_lines = 22
        nb_adc = 4
        bin_status = f"{status:0{nb_lines}b}"[::-1]
        
        for idx_adc in range(nb_adc):
            if idx_adc < 3:
                htr_states = bin_status[6*idx_adc:6*idx_adc+6]
                adc_val = random.uniform(-0.01, 0.01)
                for state in htr_states:
                    if state == '1':
                        adc_val += random.uniform(1.9/6-0.01, 1.9/6+0.01)
            else:
                htr_states = bin_status[6*idx_adc:6*idx_adc+4]
                adc_val = random.uniform(-0.01, 0.01)
                for state in htr_states:
                    if state == '1':
                        adc_val += random.uniform(1.9/4-0.01, 1.9/4+0.01)
            converted_values.append(adc_val)
    
    elif LogicalUnitIdn == "ReactionWheelEnSel":
        nb_lines = 4
        nb_adc = 4
        bin_status = f"{status:0{nb_lines}b}"[::-1]
        
        for idx_adc in range(nb_adc):
            rw_states = bin_status[1*idx_adc:1*idx_adc+1]
            adc_val = random.uniform(-0.01, 0.01)
            for state in rw_states:
                if state == '1':
                    adc_val += random.uniform(5/1-0.01, 5/1+0.01)
            converted_values.append(adc_val)
    
    elif LogicalUnitIdn == "PropEnSel":
        nb_lines = 2
        nb_adc = 2
        bin_status = f"{status:0{nb_lines}b}"[::-1]
        
        for idx_adc in range(nb_adc):
            prop_states = bin_status[1*idx_adc:1*idx_adc+1]
            adc_val = random.uniform(-0.01, 0.01)
            for state in prop_states:
                if state == '1':
                    adc_val += random.uniform(40/1-0.01, 40/1+0.01)
            converted_values.append(adc_val)
    
    elif LogicalUnitIdn == "AvionicLoadEnSel":
        nb_lines = 2
        nb_adc = 2
        bin_status = f"{status:0{nb_lines}b}"[::-1]
        
        for idx_adc in range(nb_adc):
            avio_states = bin_status[idx_adc]
            adc_val = random.uniform(-0.01, 0.01)
            for state in avio_states:
                if state == '1':
                    adc_val += random.uniform(0.2/1-0.01, 0.2/1+0.01)
            converted_values.append(adc_val)
    
    elif LogicalUnitIdn == "HdrmEnSel":
        nb_lines = 12
        nb_adc = 16
        bin_status = f"{status:0{nb_lines}b}"[::-1]
        LOGGER.info(f"bin_status: {bin_status}")
        
        nom_arm_status = 1
        red_arm_status = 1
        
        for idx_adc in range(nb_adc):
            adc_val = random.uniform(-0.01, 0.01)
            
            if idx_adc in [2, 3, 4, 5, 6]:  # Nom voltage
                if nom_arm_status and bin_status[idx_adc] == '1':
                    adc_val = random.uniform(28-0.01, 28+0.01)
            elif idx_adc in [7, 8, 9, 10, 11]:  # Red voltage
                if red_arm_status and bin_status[idx_adc] == '1':
                    adc_val = random.uniform(28-0.01, 28+0.01)
            elif idx_adc == 12:  # Arm voltage Nom
                if nom_arm_status:
                    adc_val = random.uniform(28-0.01, 28+0.01)
            elif idx_adc == 13:  # Arm voltage Red
                if red_arm_status:
                    adc_val = random.uniform(28-0.01, 28+0.01)
            elif idx_adc == 14:  # group current Nom
                if nom_arm_status:
                    for state in bin_status[1:7]:
                        if state == '1':
                            adc_val += random.uniform(4/6-0.01, 4/6+0.01)
            elif idx_adc == 15:  # group current Red
                if red_arm_status:
                    for state in bin_status[8:]:
                        if state == '1':
                            adc_val += random.uniform(4/6-0.01, 4/6+0.01)
            
            converted_values.append(adc_val)
    
    elif LogicalUnitIdn == "ThermAndFlybackEnSel":
        nb_adc = 5
        for idx_adc in range(nb_adc):
            adc_val = random.uniform(5-0.01, 5+0.01)
            converted_values.append(adc_val)
    
    # Update converted and raw measurements
    if converted_values:
        adc_sel_name = LogicalUnitIdn.replace("EnSel", "AdcSel")
        setattr(unit.converted_measurements, adc_sel_name, converted_values)
        
        raw_values = [int.from_bytes(struct.pack("!e", val), "big") for val in converted_values]
        setattr(unit.raw_measurements, adc_sel_name, raw_values)


def ResetUnitPwLines(ResetUnitPwLines, apid, state_manager):
    """Reset unit power lines"""
    unit = state_manager.get_unit(apid)
    
    LogicalUnitIdn = LogicalUnitId[ResetUnitPwLines["ResetUnitPwLines"]["LogicUnitId"]]
    LOGGER.info(f"LogicalUnitId: {LogicalUnitIdn}")
    
    NewItem_ResetUnitPwLines = ResetUnitPwLines["ResetUnitPwLines"]["Parameters"]
    setattr(unit.unit_line_states, LogicalUnitIdn, NewItem_ResetUnitPwLines)


def OverwriteUnitPwLines(OverwriteUnitPwLines, apid, state_manager):
    """Overwrite unit power lines"""
    unit = state_manager.get_unit(apid)
    
    LogicalUnitIdn = LogicalUnitId[OverwriteUnitPwLines["OverwriteUnitPwLines"]["LogicUnitId"]]
    LOGGER.info(f"LogicalUnitId: {LogicalUnitIdn}")
    
    NewItem_OverwriteUnitPwLines = OverwriteUnitPwLines["OverwriteUnitPwLines"]["Parameters"]
    setattr(unit.unit_line_states, LogicalUnitIdn, NewItem_OverwriteUnitPwLines)


def GetRawMeasurements(RawMeasurements, apid, state_manager):
    """Get raw measurements"""
    unit = state_manager.get_unit(apid)
    
    Unit_Lines_Str = GetUnitLineStates(RawMeasurements, apid, state_manager)
    Unit_Lines = json.loads(Unit_Lines_Str)
    Unit_Lines_Status = Unit_Lines["PduUnitLineStates"]
    LogicId = RawMeasurements["GetRawMeasurements"]["LogicUnitId"]
    Single_Line_Status = Unit_Lines_Status[LogicalUnitId[int(LogicId)]]
    
    LOGGER.info(f"Single_Line_Status: {Single_Line_Status}")
    
    if int(Single_Line_Status) != 0:
        return json.dumps(unit.raw_measurements.to_dict())
    else:
        # Return empty measurements
        from pdu_state import PduRawMeasurementsState
        return json.dumps(PduRawMeasurementsState().to_dict())


def GetConvertedMeasurements(ConvertedMeasurements, apid, state_manager):
    """Get converted measurements"""
    unit = state_manager.get_unit(apid)
    
    Unit_Lines_Str = GetUnitLineStates(ConvertedMeasurements, apid, state_manager)
    Unit_Lines = json.loads(Unit_Lines_Str)
    Unit_Lines_Status = Unit_Lines["PduUnitLineStates"]
    LogicId = ConvertedMeasurements["GetConvertedMeasurements"]["LogicUnitId"]
    Single_Line_Status = Unit_Lines_Status[LogicalUnitId[int(LogicId)]]
    
    LOGGER.info(f"Single_Line_Status: {Single_Line_Status}")
    
    if int(Single_Line_Status) != 0:
        return json.dumps(unit.converted_measurements.to_dict())
    else:
        # Return empty measurements
        from pdu_state import PduConvertedMeasurementsState
        return json.dumps(PduConvertedMeasurementsState().to_dict())


def GetConvertedMeasurementsPeriodic(ConvertedMeasurements, apid, state_manager):
    """Get converted measurements periodically"""
    unit = state_manager.get_unit(apid)
    
    pdu_converted_tlm = {"PduConvertedMeasurements": {}}
    Unit_Lines_Str = GetUnitLineStates(ConvertedMeasurements, apid, state_manager)
    Unit_Lines = json.loads(Unit_Lines_Str)
    Unit_Lines_Status = Unit_Lines["PduUnitLineStates"]
    
    converted_dict = unit.converted_measurements.to_dict()["PduConvertedMeasurements"]
    
    for logic_id in range(0, 9):
        Single_Line_Status = Unit_Lines_Status[LogicalUnitId[int(logic_id)]]
        LOGGER.info(f"Single_Line_Status: {Single_Line_Status}")
        
        if int(Single_Line_Status) != 0:
            pdu_converted_tlm["PduConvertedMeasurements"].update({
                LogicalUnitId[int(logic_id)]: converted_dict[LogicalUnitId[int(logic_id)].replace("EnSel", "AdcSel")]
            })
    
    return json.dumps(pdu_converted_tlm)


def PduGoTo(cmd, apid, state_manager):
    """Change PDU state"""
    unit = state_manager.get_unit(apid)
    unit.pdu_status.PduState = PduState[cmd]
    LOGGER.info(f"PDU state changed to: {cmd} ({PduState[cmd]})")
