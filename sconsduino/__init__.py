import os.path

ARDUINO_VER = 105

class Arduino(object):
	def __init__(self, sketch, env, src_dir=None, build_dir=None, **kw):
		self.env = env
		self.objects = []
		self._load_config()
		self.env.Append(
			ARDUINO=self.config['ARDUINO_DIR'],
			CPPPATH = [],
			CPPDEFINES = {'ARDUINO': ARDUINO_VER},
			# C/C++
			CCFLAGS=['-c', '-g', '-Os', '-Wall', '-ffunction-sections', '-fdata-sections', '-MMD'],
			# C only
			CFLAGS=['-std=gnu11'],
			# C++ only
			CXXFLAGS=['-fno-exceptions', '-fno-rtti', '-felide-constructors', '-std=gnu++11'],
			LINKFLAGS=['-Os', '-Wl,--gc-sections'],
			BUILDERS={
				'Eep': self.env.Builder(action='$OBJCOPY -O ihex -j .eeprom --set-section-flags=.eeprom=alloc,load --no-change-warnings --change-section-lma .eeprom=0 $SOURCE $TARGET',
					suffix='.eep',
					src_suffix='.elf',
					),
				'Hex': self.env.Builder(action='$OBJCOPY -O ihex -R .eeprom $SOURCE $TARGET',
					suffix='.hex',
					src_suffix='.elf',
					),
				'Upload': self.env.Builder(action=self._write_upload_script,
					src_suffix='.hex')
			}
		)
		self.build_dir = self.env.Dir(build_dir or '.')

	def _load_config(self):
		# FIXME: use a real config file
		self.config = {}
		try:
			execfile(os.path.expanduser("~/.arduino-scons"), self.config)
		except:
			print "WARNING: Unconfigured. Using defaults..."
			self.config = dict(
				ARDUINO_DIR = "/usr/share/arduino",
			)

		# Verify
		if not os.path.exists(self.config['ARDUINO_DIR']):
			self.env.Exit("Misconfigured ARDUINO_DIR: {:r}".format(ARDUINO_DIR))

	def add_generator(self, srcs):
		"""

		"""
		for src in srcs:
			self.add(src)

	def cpu(self, speed):
		"""
		Configure CPU settings, namely speed
		"""
		self.env.Append(
			CPPDEFINES = {'F_CPU': speed}
		)

	def usb(self, vid, pid):
		"""
		Configure USB settings
		"""
		self.env.Append(
			CPPDEFINES = {'USB_VID': vid, 'USB_PID': pid}
		)

	def libs(self, *libs):
		"""
		Add Arduino libraries
		"""
		pass

	def _find_tools(self, d, **kw):
		d = str(d)
		f = "{}"
		if 'prefix' in kw:
			f = kw['prefix']+f
		if 'suffix' in kw:
			f = f+kw['suffix']
		return {
			v: os.path.join(d, f.format(t))
			for v,t in (('CC', 'gcc'), ('CXX', 'g++'), ('OBJCOPY', 'objcopy'), ('SIZE', 'size'))
			if os.path.exists(os.path.join(d, f.format(t)))
		}

	def add(self, src):
		base, ext = os.path.splitext(os.path.basename(str(src)))
		if ext not in ('.c', '.cpp'):
			raise ValueError("Unknown extension: {}".format(ext))
		self.objects += self.env.Object(self.build_dir.File(base+'.o'), src)

	def sketch(self, sketch):
		elf = self.env.Program(sketch+'.elf', self.objects)
		eep = self.env.Eep(sketch+'.eep', elf)
		hex = self.env.Hex(sketch+'.hex', elf)
		self.env.Upload('upload', hex)

	def _write_upload_script(self, target, source, env):
			for trgt, src in zip(target, source):
				with open(unicode(trgt), 'w') as upscript:
					upscript.write("""#!/bin/sh
exec {}
""".format(self.upload_command(target, source, env))
					)
					os.fchmod(upscript.fileno(), 0755)
					print "Run ./{} to upload {}".format(trgt, src)

	def upload_command(self, target, source, env):
		raise NotImplementedError()