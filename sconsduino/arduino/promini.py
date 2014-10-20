from .. import Arduino
import stat
import os

class ProMini(Arduino):
	PARTS = {
		328: 'atmega328p',
		168: 'atmega168',
	}
	SPEED = {
		5.0: 16000000,
		3.3:  8000000
	}

	def __init__(self, *p, **kw):
		super(ProMini, self).__init__(*p, **kw)
		self.chip = kw['chip']
		if self.chip not in self.PARTS:
			raise ValueError("chip must be 168 or 328")
		self.volt = float(kw['V'])
		if self.volt not in self.SPEED:
			raise ValueError("V must be 5 or 3.3")

		self.cpu(self.SPEED[self.volt])

		self.env.Append(
			COREPATH=self.env.Dir("$ARDUINO").Dir('hardware').Dir('arduino').Dir('cores').Dir('arduino'),
			CPPPATH=['$COREPATH', self.env.Dir("$ARDUINO").Dir("hardware").Dir("arduino").Dir("variants").Dir("standard")],
			MCU=self.PARTS[self.chip],
			# C/C++
			CCFLAGS=['-mmcu=$MCU'],
			# C only
			CFLAGS=[],
			# C++ only
			CXXFLAGS=[],
			LINKFLAGS=['-mmcu=$MCU'],
			LIBS=['m'],
			LOAD='avrdude', # /home/james/.local/arduino/hardware/tools/avrdude -C$(ARDUINO)/hardware/tools/avrdude.conf -patmega328p -cstk500v1 -P$(SER) -b19200 -Uflash:w:$<.hex:i 
			LOADFLAGS=[],
		)
		self.env.Replace(
			**self._find_tools(self.env.Dir("$ARDUINO").Dir('hardware').Dir('tools').Dir('avr').Dir('bin'), prefix='avr-')
		)
		self._find_core(self.env['COREPATH'])

	def default_config(self):
		d = super(ProMini, self).default_config()
		d.update(
			SERIAL_PORT = '/dev/ttyUSB0',
		)
		return d

	def verify_config(self):
		super(ProMini, self).verify_config()
		if not stat.S_ISCHR(os.stat(self.config['SERIAL_PORT']).st_mode):
			self.env.Exit("SERIAL_PORT not a character device")

	def upload_command(self):
		if self.chip == 328:
			baud = 57600
		elif self.chip == 168:
			baud = 19200
		return "$ARDUINO/hardware/tools/avrdude -C$ARDUINO/hardware/tools/avrdude.conf -p$MCU -carduino -P{} -b{} -D -Uflash:w:$SOURCE:i".format(self.config['SERIAL_PORT'], baud)

