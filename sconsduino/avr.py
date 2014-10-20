# -*- coding: utf-8 -*-
from __future__ import absolute_import
from . import Arduino
import os
import stat

class _FuseManager(object):
	"""
	Exposes fuse settings.

	Note that this currently forces values for RSDISBL and SPIEN, just because this is a Really Bad Idea for me.
	"""
	"""
	For all fuses “1” means unprogrammed while “0” means programmed.
	"""
	# http://www.engbedded.com/fusecalc/
	# http://eleccelerator.com/fusecalc/fusecalc.php?chip=atmega328p
	def __init__(self, parent):
		self._parent = parent
		## Set registers to default ##
		# Reset pin disabled
		self.RSDISBL = 1

		# Clock select and startup time
		self.CKSEL = 0b0010
		self.CKDIV8 = 0
		self.SUT = 0b10
		self.CKOUT = 1 # Pump out the scaled clock
		self.BODLEVEL = 0b111 # Brown-out levels

		# Bootloader options
		self.BOOTSZ = 0b00
		self.BOOTRST = 1

		# EEPROM is preserved through chip erase cycles
		self.EESAVE = 1
		
		# Watch dog timer on
		self.WDTON = 1

		# Allow SPI for programming
		self.SPIEN = 0

		# debugWIRE
		self.DWEN = 1

	def __enter__(self):
		return self

	def __exit__(self, t, v, tb):
		if t is None:
			f = self.fuses()
			print("Fuses: l:{:02X} h:{:02X} e:{:02X}".format(*f))
			self._parent.fuses = f

	def fuses(self):
		ext = (self.BODLEVEL & 0b111) # Table 28-6
		# First constant hard-codes RSTDISBL, DWEN, and SPIEN (so we don't brick our chip)
		high = (0b11000000) | ((self.WDTON & 1) << 4) | ((self.EESAVE & 1) << 3) | ((self.BOOTSZ & 0b11) << 1) | (self.BOOTRST & 1) # Table 28-8
		low = ((self.CKDIV8 & 1) << 7) | ((self.CKOUT & 1) << 6) | ((self.SUT & 0b11) << 4) | (self.CKSEL & 0b1111) # Table 28-9
		return low, high, ext

	def clock(self, src, speed=None, div=True):
		"""
		src - One of lpco, fsco, lfco, intern128, internal, external
		speed - Speed in MHz (if applicable)
		"""
		"""
		(9-1)
		Low Power Crystal Oscillator      1111 - 1000
		Full Swing Crystal Oscillator     0111 - 0110
		Low Frequency Crystal Oscillator  0101 - 0100
		Internal 128kHz RC Oscillator     0011
		Calibrated Internal RC Oscillator 0010
		External Clock                    0000


		Low Power Crystal Oscillator Operating Modes (9-3)
		0.4 -  0.9 MHz  100
		0.9 -  3.0 MHz  101
		3.0 -  8.0 MHz  110
		8.0 - 16.0 MHz  111


		Full Swing Crystal Oscillator (9-5)
		0.4 - 20 MHz  011
		
		Internal Calibrated RC Oscillator Operating Modes (9-11)
		7.3 - 8.1 MHz  0010
		
		128kHz Internal Oscillator Operating Modes (9-13)
		128kHz  0011

		External Clock Frequency (9-15)
		0 - 20 MHz  0000
		"""
		self.CKDIV8 = 0 if div else 1  # Might not be allowed with Arduino
		if src == 'lpco':
			if 0.4 <= speed < 0.9:
				v = 0b1000
			elif 0.9 <= speed < 3.0:
				v = 0b1010
			elif 3.0 <= speed < 8.0:
				v = 0b1100
			elif 8.0 <= speed < 16:
				v = 0b1110
			else:
				raise ValueError("Unknown value for speed: {:r}".format(speed))
			self.CKSEL = v | (self.CKSEL & 1)
		elif src == 'fsco':
			self.CKSEL = 0b0110 | (self.CKSEL & 1)
		elif src == 'lfco':
			self.CKSEL = 0b0100 | (self.CKSEL & 1)
		elif src == 'intern128':
			self.CKSEL = 0b0011
			if speed is None:
				speed = 0.128
		elif src == 'internal':
			self.CKSEL = 0b0010
			if speed is None:
				speed = 7.7 # Mean of 7.3-8.1
		elif src == 'external':
			self.CKSEL = 0b0000
		else:
			raise ValueError("Unknown value for src: {:r}".format(src))

		if speed is not None:
			print "CKDIV8", self.CKDIV8, div
			if self.CKDIV8: # 1== Do not divide by 8
				print "WARNING: Disabling CKDIV8 is unsupported"
				hz = speed*1000000
			else:
				hz = speed*1000000 / 8 * 2  # Dunno why the 2. Just determined experimentally
			self._parent.cpu(hz)

	def startup(self, kind, type=None, borderline=False):
		"""
		Must be called after clock()
		kind - one of fast, slow, bod
		type - one of ceramic, crystal (if applicable)
		borderline - if True, use ultra-fast start times (ceramic only, see footnotes in datasheet)
		"""
		src = self.CKSEL & 0b1110

		# Start-up Times for the Low Power Crystal Oscillator Clock Selection (9-4)
		# Ceramic resonator, fast rising power    258 CK  14CK + 4.1ms 0 00 
		# Ceramic resonator, slowly rising power  258 CK  14CK + 65ms  0 01

		# Ceramic resonator, BOD enabled          1K CK   14CK         0 10
		# Ceramic resonator, fast rising power    1K CK   14CK + 4.1ms 0 11
		# Ceramic resonator, slowly rising power  1K CK   14CK + 65ms  1 00

		# Crystal Oscillator, BOD enabled         16K CK  14CK         1 01 
		# Crystal Oscillator, fast rising power   16K CK  14CK + 4.1ms 1 10 
		# Crystal Oscillator, slowly rising power 16K CK  14CK + 65ms  1 11
		if src in (0b1000, 0b1010, 0b1100, 0b1110): # LPCO
			if kind == 'fast' and type == 'ceramic' and borderline:
				self.CKSEL = src | 0
				self.SUT = 0b00
			elif kind == 'slow' and type == 'ceramic' and borderline:
				self.CKSEL = src | 0
				self.SUT = 0b01
			elif kind == 'bod' and type == 'ceramic' and not borderline:
				self.CKSEL = src | 0
				self.SUT = 0b10
			elif kind == 'fast' and type == 'ceramic' and not borderline:
				self.CKSEL = src | 0
				self.SUT = 0b11
			elif kind == 'slow' and type == 'ceramic' and not borderline:
				self.CKSEL = src | 1
				self.SUT = 0b00
			elif kind == 'bod' and type == 'crystal' and not borderline:
				self.CKSEL = src | 1
				self.SUT = 0b01
			elif kind == 'fast' and type == 'crystal' and not borderline:
				self.CKSEL = src | 1
				self.SUT = 0b10
			elif kind == 'slow' and type == 'crystal' and not borderline:
				self.CKSEL = src | 1
				self.SUT = 0b11
			else:
				raise ValueError("Invalid configuration for Low Power Crystal Oscillator: {} {} {}".format (kind, type, borderline))

		# Start-up Times for the Full Swing Crystal Oscillator Clock Selection (9-6)
		# Ceramic resonator, fast rising power    258 CK  14CK + 4.1ms 0 00
		# Ceramic resonator, slowly rising power  258 CK  14CK + 65ms  0 01

		# Ceramic resonator, BOD enabled          1K CK   14CK         0 10
		# Ceramic resonator, fast rising power    1K CK   14CK + 4.1ms 0 11
		# Ceramic resonator, slowly rising power  1K CK   14CK + 65ms  1 00

		# Crystal Oscillator, BOD enabled         16K CK  14CK         1 01
		# Crystal Oscillator, fast rising power   16K CK  14CK + 4.1ms 1 10
		# Crystal Oscillator, slowly rising power 16K CK  14CK + 65ms  1 11
		elif src == 0b0110: # FSCO
			if type == 'ceramic' and kind == 'fast' and borderline:
				self.CKSEL = src | 0
				self.SUT = 0b00
			elif type == 'ceramic' and kind == 'slow' and borderline:
				self.CKSEL = src | 0
				self.SUT = 0b01
			elif type == 'ceramic' and kind == 'bod' and not borderline:
				self.CKSEL = src | 0
				self.SUT = 0b10
			elif type == 'ceramic' and kind == 'fast' and not borderline:
				self.CKSEL = src | 0
				self.SUT = 0b11
			elif type == 'ceramic' and kind == 'slow' and not borderline:
				self.CKSEL = src | 1
				self.SUT = 0b00
			elif type == 'crystal' and kind == 'bod' and not borderline:
				self.CKSEL = src | 1
				self.SUT = 0b01
			elif type == 'crystal' and kind == 'fast' and not borderline:
				self.CKSEL = src | 1
				self.SUT = 0b10
			elif type == 'crystal' and kind == 'slow' and not borderline:
				self.CKSEL = src | 1
				self.SUT = 0b11
			else:
				raise ValueError("Invalid configuration for Full Swing Crystal Oscillator: {} {} {}".format (kind, type, borderline))

		# Start-up Times for the Low-frequency Crystal Oscillator Clock Selection (9-9)
		# 00  4 CK         Fast rising power or BOD enabled
		# 01  4 CK + 4.1ms Slowly rising power
		# 10  4 CK + 65ms  Stable frequency at start-up

		# Start-up Times for the Low-frequency Crystal Oscillator Clock Selection (9-10)
		# 0100  1K CK
		# 0101  32K CK  Stable frequency at start-up
		elif src == 0b0110: # LFCO
			raise NotImplementedError("Too complicated! Ahh!")


		# Start-up times for the internal calibrated RC Oscillator clock selection (9-12)
		# BOD enabled         6 CK  14CK          00
		# Fast rising power   6 CK  14CK + 4.1ms  01
		# Slowly rising power 6 CK  14CK + 65ms   10
		elif self.CKSEL == 0b0010:
			if kind == 'bod':
				self.SUT = 0b00
			elif kind == 'fast':
				self.SUT = 0b01
			elif kind == 'slow':
				self.SUT = 0b10
			else:
				raise ValueError("Invalid configuration for internal calibrated RC oscillator clock: {} {} {}".format (kind, type, borderline))

		# Start-up Times for the 128kHz Internal Oscillator (9-14)
		# BOD enabled         6 CK  14CK        00
		# Fast rising power   6 CK  14CK + 4ms  01
		# Slowly rising power 6 CK  14CK + 64ms 10
		elif self.CKSEL == 0b0011:
			if kind == 'bod':
				self.SUT = 0b00
			elif kind == 'fast':
				self.SUT = 0b01
			elif kind == 'slow':
				self.SUT = 0b10
			else:
				raise ValueError("Invalid configuration for 128kHz internal RC oscillator: {} {} {}".format (kind, type, borderline))


		# Start-up Times for the External Clock Selection (9-16)
		# BOD enabled         6 CK  14CK         00
		# Fast rising power   6 CK  14CK + 4.1ms 01
		# Slowly rising power 6 CK  14CK + 65ms  10
		elif self.CKSEL == 0b0000:
			if kind == 'bod':
				self.SUT = 0b00
			elif kind == 'fast':
				self.SUT = 0b01
			elif kind == 'slow':
				self.SUT = 0b10
			else:
				raise ValueError("Invalid configuration for external clock: {} {} {}".format (kind, type, borderline))


	def brownout(self, V):
		"""
		BODLEVEL Fuse Coding (29-17)
		111  BOD Disabled
		110  1.7-2.0V  1.8V
		101  2.5-2.9V  2.7V
		100  4.1-4.3V  4.5V
		"""
		VALUES = {
			None: 0b111,
			2.0: 0b110,
			2.9: 0b101,
			4.5: 0b100,
		}
		self.BODLEVEL = VALUES[V]


	def watchdog(self, on):
		"""
		Enable the Watchdog Timer in fuses.

		NOTE: This forces the WDT to reset the chip, interrupt mode is disabled.
		"""
		self.WDTON = 0 if on else 1

	def eesave(self, on):
		"""
		Save EEPROM across chip resets.
		"""
		self.EESAVE = 0 if on else 1

	def bootloader(self, size):
		""
		"""
		Boot Size Configuration, ATmega328/328P (27-13)
		11  256 words   4  0x0000 - 0x3EFF  0x3F00 - 0x3FFF  0x3EFF  0x3F00
		10  512 words   8  0x0000 - 0x3DFF  0x3E00 - 0x3FFF  0x3DFF  0x3E00
		01 1024 words  16  0x0000 - 0x3BFF  0x3C00 - 0x3FFF  0x3BFF  0x3C00
		00 2048 words  32  0x0000 - 0x37FF  0x3800 - 0x3FFF  0x37FF  0x3800
		"""
		SIZES = {
			256: 0b11,
			512: 0b10,
			1024: 0b01,
			2048: 0b00,
		}
		if size is None:
			self.BOOTRST = 1
		else:
			self.BOOTRST = 0
			self.BOOTSZ = SIZES[size]

	def debugWIRE(self, on):
		self.DWEN = 0 if on else 1

class Atmega328(Arduino):
	"""
	A bare ATMEGA328

	Supported chips: ATmega328/P
	"""

	def __init__(self, *p, **kw):
		super(Atmega328, self).__init__(*p, **kw)
		self.partno = kw['partno']
		self.env.Append(
			COREPATH=self.env.Dir("$ARDUINO").Dir('hardware').Dir('arduino').Dir('cores').Dir('arduino'),
			CPPPATH=['$COREPATH', self.env.Dir("$ARDUINO").Dir("hardware").Dir("arduino").Dir("variants").Dir("standard")],
			# C/C++
			CCFLAGS=['-mmcu='+self.partno],
			# C only
			CFLAGS=[],
			# C++ only
			CXXFLAGS=[],
			LINKFLAGS=['-mmcu='+self.partno],
			LIBS=['m'],
			LOAD='avrdude', # /home/james/.local/arduino/hardware/tools/avrdude -C$(ARDUINO)/hardware/tools/avrdude.conf -patmega328p -cstk500v1 -P$(SER) -b19200 -Uflash:w:$<.hex:i 
			LOADFLAGS=[],
		)
		self.env.Replace(
			**self._find_tools(self.env.Dir("$ARDUINO").Dir('hardware').Dir('tools').Dir('avr').Dir('bin'), prefix='avr-')
		)
		self._find_core(self.env['COREPATH'])

	def fuses(self):
		return _FuseManager(self)

	def default_config(self):
		d = super(Atmega328, self).default_config()
		d.update(
			SERIAL_PORT = '/dev/ttyACM0',
		)
		return d

	def verify_config(self):
		super(Atmega328, self).verify_config()
		if not stat.S_ISCHR(os.stat(self.config['SERIAL_PORT']).st_mode):
			self.env.Exit("SERIAL_PORT not a character device")

	def upload_command(self):
		f = ""
		if hasattr(self, 'fuses'):
			f = "-Ulfuse:w:0x{:02x}:m -Uhfuse:w:0x{:02x}:m -Uefuse:w:0x{:02x}:m".format(*self.fuses)
		return "$ARDUINO/hardware/tools/avrdude -C$ARDUINO/hardware/tools/avrdude.conf -patmega328p -cstk500v1 -P{} -b19200 {} -Uflash:w:$SOURCE:i".format(self.config['SERIAL_PORT'], f)
