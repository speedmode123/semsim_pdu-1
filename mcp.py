import smbus2
import time
from enum import IntEnum


class GPIO_PINS(IntEnum):
	''' Pins on a MCP23017 Device
	'''
	GPA0 = 0
	GPA1 = 1
	GPA2 = 2
	GPA3 = 3
	GPA4 = 4
	GPA5 = 5
	GPA6 = 6
	GPA7 = 7
	GPB0 = 8
	GPB1 = 9
	GPB2 = 10
	GPB3 = 11
	GPB4 = 12
	GPB5 = 13
	GPB6 = 14
	GPB7 = 15

#List of Register addresses
class MCP23017_REGISTERS(IntEnum):
	''' Registers on a MCP23017 Device'''

	MCP23017_IODIRA = 0x00 
	MCP23017_IPOLA  = 0x02 
	MCP23017_GPINTENA = 0x04
	MCP23017_DEFVALA = 0x06 
	MCP23017_INTCONA = 0x08 
	MCP23017_IOCONA = 0x0A 
	MCP23017_GPPUA = 0x0C 
	MCP23017_INTFA = 0x0E 
	MCP23017_INTCAPA = 0x10 
	MCP23017_GPIOA = 0x12   
	MCP23017_OLATA = 0x14  

	MCP23017_IODIRB = 0x01
	MCP23017_IPOLB = 0x03
	MCP23017_GPINTENB = 0x05
	MCP23017_DEFVALB = 0x07
	MCP23017_INTCONB = 0x09
	MCP23017_IOCONB = 0x0B
	MCP23017_GPPUB = 0x0D
	MCP23017_INTFB = 0x0F
	MCP23017_INTCAPB = 0x11
	MCP23017_GPIOB = 0x13
	MCP23017_OLATB = 0x15


#MCP23017_IOCONA configuration
class IOCON_CONFIGURATION(IntEnum):
	"""Bit configuration of the IOCON Register on a MCP23017 Device"""
	BANK_BIT    = 7
	MIRROR_BIT  = 6
	SEQOP_BIT   = 5
	DISSLW_BIT  = 4
	HAEN_BIT    = 3
	ODR_BIT     = 2
	INTPOL_BIT  = 1

class PIN_LEVELS(IntEnum):
	"""Digital Pin levels on a MCP23017 Device"""
	HIGH = 0xFF
	LOW = 0x00

class PIN_DIRECTIONS(IntEnum):
	"""Pin Modes/Directions"""
	INPUT = 0xFF
	OUTPUT = 0x00

class PULLUP_SWITCH_STATE(IntEnum):
	"""Pullup and Pulldown states for pins on a MC23017 Device"""
	PULLUP = 0xFF	
	PULLDOWN = 0x00	

#   Addr(BIN)      Addr(hex)
#XXX X  A2 A1 A0
#010 0  1  1  1      0x27 
#010 0  1  1  0      0x26 
#010 0  1  0  1      0x25 
#010 0  1  0  0      0x24 
#010 0  0  1  1      0x23 
#010 0  0  1  0      0x22
#010 0  0  0  1      0x21
#010 0  0  0  0      0x20

#	RegName  |ADR | bit7    | bit6   | bit5   | bit4   | bit3   | bit2   | bit1   | bit0   | POR/RST
#	--------------------------------------------------------------------------------------------------
#	IODIRA   | 00 | IO7     | IO6    | IO5    | IO4    | IO3    | IO2    | IO1    | IO0    | 1111 1111
#	IODIRB   | 01 | IO7     | IO6    | IO5    | IO4    | IO3    | IO2    | IO1    | IO0    | 1111 1111
#	IPOLA    | 02 | IP7     | IP6    | IP5    | IP4    | IP3    | IP2    | IP1    | IP0    | 0000 0000
#	IPOLB    | 03 | IP7     | IP6    | IP5    | IP4    | IP3    | IP2    | IP1    | IP0    | 0000 0000
#	GPINTENA | 04 | GPINT7  | GPINT6 | GPINT5 | GPINT4 | GPINT3 | GPINT2 | GPINT1 | GPINT0 | 0000 0000
#	GPINTENB | 05 | GPINT7  | GPINT6 | GPINT5 | GPINT4 | GPINT3 | GPINT2 | GPINT1 | GPINT0 | 0000 0000
#	DEFVALA  | 06 | DEF7    | DEF6   | DEF5   | DEF4   | DEF3   | DEF2   | DEF1   | DEF0   | 0000 0000
#	DEFVALB  | 07 | DEF7    | DEF6   | DEF5   | DEF4   | DEF3   | DEF2   | DEF1   | DEF0   | 0000 0000
#	INTCONA  | 08 | IOC7    | IOC6   | IOC5   | IOC4   | IOC3   | IOC2   | IOC1   | IOC0   | 0000 0000
#	INTCONB  | 09 | IOC7    | IOC6   | IOC5   | IOC4   | IOC3   | IOC2   | IOC1   | IOC0   | 0000 0000
#	IOCON    | 0A | BANK    | MIRROR | SEQOP  | DISSLW | HAEN   | ODR    | INTPOL | -      | 0000 0000
#	IOCON    | 0B | BANK    | MIRROR | SEQOP  | DISSLW | HAEN   | ODR    | INTPOL | -      | 0000 0000
#	GPPUA    | 0C | PU7     | PU6    | PU5    | PU4    | PU3    | PU2    | PU1    | PU0    | 0000 0000
#	GPPUB    | 0D | PU7     | PU6    | PU5    | PU4    | PU3    | PU2    | PU1    | PU0    | 0000 0000



class MCP23017:
	"""Represents a MCP driver for use with MC23017 Expander.

    Attributes:\n
        address (int): Address of the device.
		bus(SMBus2 Object): Object for reading and decoding information from an I2C bus
    """

	def __init__(self, address):
		self.address = address			
		self.bus = smbus2.SMBus(1)
		
	def __del__(self):
		self.bus.close()

	def set_all_output(self):
		""" sets all GPIO pins as OUTPUT"""
		self.bus.write_byte_data(self.address, MCP23017_REGISTERS.MCP23017_IODIRA.value, PIN_DIRECTIONS.OUTPUT.value)
		self.bus.write_byte_data(self.address, MCP23017_REGISTERS.MCP23017_IODIRB.value, PIN_DIRECTIONS.OUTPUT.value)

	def set_all_input(self):
		""" sets all GPIO pins as INPUT"""
		self.bus.write_byte_data(self.address, MCP23017_REGISTERS.MCP23017_IODIRA.value, PIN_DIRECTIONS.INPUT.value)
		self.bus.write_byte_data(self.address, MCP23017_REGISTERS.MCP23017_IODIRB.value, PIN_DIRECTIONS.INPUT.value)

	def set_pin_direction(self, gpio_pin, direction):
		""" sets given GPIO pin to either input or output
		
		Args:
			gpio_pin (int): corresponding to a particular pin on the expander board	
			direction (int): whether input (1) or output (0)
		"""
		pair = self.get_register_gpio_tuple([MCP23017_REGISTERS.MCP23017_IODIRA.value, MCP23017_REGISTERS.MCP23017_IODIRB.value], gpio_pin)
		self.set_bit_enabled(pair[0], pair[1],True if direction is PIN_DIRECTIONS.INPUT.value else False)

	def set_b_pins_at_pull_up(self):
		self.bus.write_byte_data(self.address, MCP23017_REGISTERS.MCP23017_GPPUB.value, PULLUP_SWITCH_STATE.PULLUP.value) 

	def set_b_pins_at_pull_down(self):
		self.bus.write_byte_data(self.address, MCP23017_REGISTERS.MCP23017_GPPUB.value, PULLUP_SWITCH_STATE.PULLDOWN.value) 	

	def set_all_pins_at_pull_up(self):
		""" configue all Pin pullUP"""
		self.bus.write_byte_data(self.address, MCP23017_REGISTERS.MCP23017_GPPUA.value, PULLUP_SWITCH_STATE.PULLUP.value) 	
		self.bus.write_byte_data(self.address, MCP23017_REGISTERS.MCP23017_GPPUB.value, PULLUP_SWITCH_STATE.PULLUP.value)
		
	def set_all_pins_at_pull_down(self):
		""" configue all Pin pullUP"""
		self.bus.write_byte_data(self.address, MCP23017_REGISTERS.MCP23017_GPPUA.value, PULLUP_SWITCH_STATE.PULLDOWN.value) 	
		self.bus.write_byte_data(self.address, MCP23017_REGISTERS.MCP23017_GPPUB.value, PULLUP_SWITCH_STATE.PULLDOWN.value) 

	def set_all_pins_to_low_level(self):
		""" configue all Pin output low level """
		self.bus.write_byte_data(self.address, MCP23017_REGISTERS.MCP23017_GPIOA.value, PIN_LEVELS.LOW.value)
		self.bus.write_byte_data(self.address, MCP23017_REGISTERS.MCP23017_GPIOB.value, PIN_LEVELS.LOW.value)

	def set_all_pins_to_high_level(self):
		""" configue all Pin output high level """
		self.bus.write_byte_data(self.address, MCP23017_REGISTERS.MCP23017_GPIOA.value, PIN_LEVELS.HIGH.value)
		self.bus.write_byte_data(self.address, MCP23017_REGISTERS.MCP23017_GPIOB.value, PIN_LEVELS.HIGH.value)

	def get_all_pins_level(self):
		"""Reads all the GPIO pins on the expander board
		
		Returns:
			status_port_a (int) : Byte value from port a corresponding to which pins are HIGH/LOW
			status_port_b (int) : Byte value from port a corresponding to which pins are HIGH/LOW
		"""
		status_port_a = self.bus.read_byte_data(self.address,MCP23017_REGISTERS.MCP23017_GPIOA.value)
		status_port_b = self.bus.read_byte_data(self.address,MCP23017_REGISTERS.MCP23017_GPIOB.value)
		return status_port_a, status_port_b

	def set_default_config(self):
		"""Sets default configuration based on table above, only the direction is set to 1 (input) """
		for addr in range(22):
			if (addr == 0) or (addr == 1):
				self.bus.write_byte_data(self.address, addr, 0xFF)
			else:
				self.bus.write_byte_data(self.address, addr, 0x00)

	def get_register_gpio_tuple(self, registers, gpio_pin):
		""" Checks which port the pin is on and returns the appropriate register
		
		Args:
			registers (list): list of integers corresponding to registers 
			gpio_pin (int): corresponding to a particular pin on the expander board
			
		Returns:
			tuple: containing the register of the correct port (A or B) and the corrected pin number
		"""
		try:
			MCP23017_REGISTERS(registers[0])
			MCP23017_REGISTERS(registers[1])
		except:
			raise TypeError("registers must contain a valid register address. See description for help")
		try:
			GPIO_PINS(gpio_pin)
		except:
			raise TypeError("pin must be one of GPAn or GPBn. See description for help")
		register = registers[0] if gpio_pin < 8 else registers[1]
		_gpio = gpio_pin % 8
		return (register, _gpio)

	def set_bit_enabled(self, register, gpio_pin, enable):
		"""enables (sets to 1) or disables (sets to 0) a particular bit in a register
		
		Args:
			register(int): register address
			gpio_pin (int): corresponding to a particular pin on the expander board	
			enable (boolean): whether to enable (TRUE) or disable (FALSE)
		"""
		stateBefore	= self.bus.read_byte_data(self.address, register)
		value = (stateBefore | self.bitmask(gpio_pin)) if enable else (stateBefore & ~self.bitmask(gpio_pin))
		self.bus.write_byte_data(self.address, register, value)

	def bitmask(self, gpio_pin):
		"""Puts the pin location into a string of bits
		
		Args:
			gpio_pin (int): corresponding to a particular pin on the expander board
			
		returns:
			int: corresponding to the location of the pin in a string of bits to be stored on the register
		"""
		return 1 << (gpio_pin % 8)

	def get_pin_level(self, gpio_pin):
		""" Reads the status of a GPIO pin 
		
		Args:
			gpio_pin (int): corresponding to a particular pin on the expander board
			
		Returns:
			int: HIGH (1) or low (0)
					
		"""
		pair = self.get_register_gpio_tuple([MCP23017_REGISTERS.MCP23017_GPIOA.value, MCP23017_REGISTERS.MCP23017_GPIOB.value], gpio_pin)
		bits = self.bus.read_byte_data(self.address, pair[0])
		return PIN_LEVELS.HIGH.value if (bits & (1 << pair[1])) > 0 else PIN_LEVELS.LOW.value

	def set_pin_level(self, gpio_pin, level):
		"""Sets the status of a GPIO pin to HIGH/LOW
		
		Args:
			gpio_pin (int): corresponding to a particular pin on the expander board
			level(int): HIGH 1 or LOW 0
		"""
		pair = self.get_register_gpio_tuple([MCP23017_REGISTERS.MCP23017_OLATA.value, MCP23017_REGISTERS.MCP23017_OLATB.value], gpio_pin)
		self.set_bit_enabled(pair[0], pair[1], True if level == PIN_LEVELS.HIGH.value else False)

	def set_all_interrupt(self, enabled):
		""" Controls Interrupt on Change control registers and sets all to specified setting. Such that when a pin changes state, a interrupt will be triggered.
		
		Args:
			enabled (boolean): whether to enable (TRUE) or disable (FALSE) interrupt on change
		"""
		self.bus.write_byte_data(self.address, MCP23017_REGISTERS.MCP23017_GPINTENA.value, 0xFF if enabled else 0x00)
		self.bus.write_byte_data(self.address, MCP23017_REGISTERS.MCP23017_GPINTENB.value, 0xFF if enabled else 0x00)

	def set_interrupt(self, gpio_pin, enabled):
		""" Controls Interrupt on Change control registers for a particular pin and sets it to specified setting.
		Such that when a pin changes state, a interrupt will be triggered for that pin.
		
		Args:
			gpio_pin (int): corresponding to a particular pin on the expander board	
			enabled (boolean): whether to enable (TRUE) or disable (FALSE) interrupt on change
		"""
		pair = self.get_register_gpio_tuple([MCP23017_REGISTERS.MCP23017_GPINTENA.value, MCP23017_REGISTERS.MCP23017_GPINTENB.value], gpio_pin)
		self.set_bit_enabled(pair[0], pair[1], enabled)

	def set_interrupt_mirror(self, enable):
		"""Controls Mirroring of Expander Configuration Register. Changes whether INTA and INTB are mirrored (triggered together).
		
		Args:
			enable (boolean): whether to enable (TRUE) or disable (FALSE) mirror bit in both IOCON registers
		"""
		self.set_bit_enabled(MCP23017_REGISTERS.MCP23017_IOCONA.value, IOCON_CONFIGURATION.MIRROR_BIT.value, enable)
		self.set_bit_enabled(MCP23017_REGISTERS.MCP23017_IOCONB.value, IOCON_CONFIGURATION.MIRROR_BIT.value, enable)

	def read_interrupt_captures(self):
		#""" Returns a tuple containing a list of the states of all the GPIO pins at the moment an interrupt occurs"
		return (self._get_list_of_interrupted_values_from(MCP23017_REGISTERS.MCP23017_INTCAPA.value), self._get_list_of_interrupted_values_from(MCP23017_REGISTERS.MCP23017_INTCAPB.value))

	def _get_list_of_interrupted_values_from(self, register):
		"""Reads the INTCAPA register which contains the state of the GPIO pins from the moment before interruption
		
		Args:
			address (int): address of the MC23017
			register(int): register address
			
		Returns:
			list: bit by bit in order of pins and their level (HIGH(1) or LOW (0)) before interruption
		
		"""
		list = []
		interrupted = self.bus.read_byte_data(self.address, register)
		bits = '{0:08b}'.format(interrupted)
		for i in reversed(range(8)):
			list.append(bits[i])
		return list

	def read_interrupt_flags(self):
		"""Reads all interrupt flags from Interrupt Flag Register
		
		Returns:
			tuple: contains list of flags (0 or 1) from ports A and B
		"""
		return (self._read_interrupt_flags_from(MCP23017_REGISTERS.MCP23017_INTFA.value), self._read_interrupt_flags_from(MCP23017_REGISTERS.MCP23017_INTFB.value))

	def _read_interrupt_flags_from(self,  register):
		"""Returns which GPIO pins triggered the interrupt as a list
		
		Args:
			address (int): address of the MC23017
			register(int): register address
			
		Returns:
			list: bit by bit in order of pins corresponding to interrupt flags (1 or 0)	
		"""
		list = []
		interrupted = self.bus.read_byte_data(self.address, register)
		bits = '{0:08b}'.format(interrupted)
		for i in reversed(range(8)):
			list.append(bits[i])
		return list



if __name__ == "__main__":
	mcp_board = MCP23017(0x26)           
	mcp_board.set_default_config()
	mcp_board.set_pin_direction(9, PIN_DIRECTIONS.INPUT) 
	# mcp_board.set_b_pins_at_pull_down()
	mcp_board.set_b_pins_at_pull_up()

	while mcp_board.get_pin_level(9):
		print("Waiting for signal")
		time.sleep(1)
	print("received pulse")

	# mcp_board = MCP23017(0x26)           
	# mcp_board.set_default_config()
	# mcp_board.set_pin_direction(6, PIN_DIRECTIONS.OUTPUT) 
	# # mcp_board.set_b_pins_at_pull_up()

	# mcp_board.set_pin_level(6, PIN_LEVELS.HIGH.value)
