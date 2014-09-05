from __future__ import absolute_import
from . import Arduino

class Atmega328(Arduino):
	"""
	A bare ATMEGA328
	"""

	def __init__(self, *p, **kw):
		super(Atmega328, self).__init__(self, *p, **kw)
		self.env.Append(
			COREPATH=self.env.Dir("$ARDUINO").Dir('hardware').Dir('arduino').Dir('cores').Dir('arduino'),
			CPPPATH=['$COREPATH', self.env.Dir("$ARDUINO").Dir("hardware").Dir("arduino").Dir("variants").Dir("standard")],
			CPPDEFINES={'TEENSYDUINO': 118},
			# C/C++
			CCFLAGS=['-mmcu=atmega328p'],
			# C only
			CFLAGS=[],
			# C++ only
			CXXFLAGS=[],
			LINKFLAGS=['-mmcu=atmega328p'],
			LIBS=['m'],
			LOAD='avrdude',
			LOADFLAGS=[],
		)
		self.env.Replace(
			**self._find_tools(self.env.Dir("$ARDUINO").Dir('hardware').Dir('tools').Dir('avr').Dir('bin'), prefix='avr-')
		)
		self._find_core(self.env['COREPATH'])
		self._finish_init()

	def upload_command(self):
		#FIXME: Figure this out
		return "false"
