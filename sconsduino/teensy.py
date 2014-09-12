from __future__ import absolute_import
from . import Arduino
import os
import subprocess

class Teensy3(Arduino):
	"""
	A Teensy3 or 3.1 board.
	"""

	def __init__(self, *p, **kw):
		super(Teensy3, self).__init__(*p, **kw)
		self.version = kw.get('version')
		self.env.Append(
			COREPATH=self.env.Dir("$ARDUINO").Dir('hardware').Dir('teensy').Dir('cores').Dir('teensy3'),
			CPPPATH=['$COREPATH'],
			CPPDEFINES={'TEENSYDUINO': 118},
			# C/C++
			CCFLAGS=['-mcpu=cortex-m4', '-mthumb', '-nostdlib'],
			# C only
			CFLAGS=['-std=gnu11'],
			# C++ only
			CXXFLAGS=['-std=gnu++11'],
			LINKFLAGS=['-mcpu=cortex-m4', '-mthumb', '-T$LDSCRIPT'],
			LIBS=['arm_cortexM4l_math', 'm'],
			LOAD='teensy_loader_cli', # TODO: run find algorithm
			LOADFLAGS=['-w', '-v'],
		)
		self.env.Replace(
			**self._find_tools(self.env.Dir("$ARDUINO").Dir('hardware').Dir('tools').Dir('arm-none-eabi').Dir('bin'), prefix='arm-none-eabi-')
		)
		if self.version == 3.0:
			self.env.Append(
				CPPDEFINES={'__MK20DX128__': ''},
				LDSCRIPT = self.env['COREPATH'].File('mk20dx128.ld'),
				MCU = 'mk20dx128',
			)
		elif self.version == 3.1:
			self.env.Append(
				CPPDEFINES={'__MK20DX256__': ''},
				LDSCRIPT = self.env['COREPATH'].File('mk20dx256.ld'),
				MCU='mk20dx256',
			)
		self._find_core(self.env['COREPATH'])
		self._finish_init()

	def usb_mode(self, mode):
		"""
		One of: SERIAL, ...
		"""
		self.env.Append(
			CPPDEFINES={'USB_'+mode: ''}
		)

	def layout(self, layout):
		"""
		One of: US_ENGLISH, CANADIAN_FRENCH, CANADIAN_MULTILINGUAL, DANISH, FINNISH, FRENCH, FRENCH_BELGIAN, FRENCH_SWISS, 
		GERMAN, GERMAN_MAC, GERMAN_SWISS, ICELANDIC, IRISH, ITALIAN, NORWEGIAN, PORTUGUESE, PORTUGUESE_BRAZILIAN, SPANISH, SPANISH_LATIN_AMERICA, 
		SWEDISH, TURKISH, UNITED_KINGDOM, US_INTERNATIONAL
		"""
		self.env.Append(
			CPPDEFINES={'LAYOUT_'+layout: ''}
		)

	def upload_command(self):
		# Has to be started now, because of scons environ mangling
		subprocess.Popen([
			os.path.join(self.env['ARDUINO'], 'hardware', 'tools', 'teensy')
		])
		return "$LOAD -mmcu=$MCU $LOADFLAGS $SOURCE"

def Teensy(*p, **kw):
	v = kw['version']
	if v in (3.0, 3.1):
		return Teensy3(*p, **kw)
	else:
		raise ValueError("Unknown Teensy version: {}".format(v))