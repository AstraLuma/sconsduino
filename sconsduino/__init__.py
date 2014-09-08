from __future__ import absolute_import
import os.path
import glob

ARDUINO_VER = 105

class Arduino(object):
	def __init__(self, sketch, env, src_dir='.', build_dir='.', **kw):
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
			CFLAGS=[],
			# C++ only
			CXXFLAGS=['-fno-exceptions', '-fno-rtti', '-felide-constructors'],
			LINKFLAGS=['-Os', '-Wl,--gc-sections'],
		)
		self.build_dir = self.env.Dir(build_dir)
		self.src_dir = self.env.Dir(src_dir)
	def _finish_init(self):
		"""
		MUST be called after all the bits have been defined.
		"""
		self.env.Append(
		)

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
		Add a thing that produces a list of sources.
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
		for l in libs:
			if os.path.exists(l):
				self.add_generator(self._find_sources(l))
				self.env.Append(CPPPATH=[lib])
			else:
			self.add_generator(self._find_sources(self.env['ARDUINO'], 'libraries', l))
			self.env.Append(CPPPATH=[os.path.join('$ARDUINO', 'libraries', l)])

	def _find_sources(self, *dirs, **kw):
		exts = kw.get('exts', ['c', 'cpp'])
		d = os.path.join(*dirs)
		d = str(d)
		for e in exts:
			for fn in glob.glob(os.path.join(d, '*.'+e)):
				yield self.env.File(fn)

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

	def _find_core(self, core):
		self.add_generator(self._find_sources(core))

	def add(self, src):
		base, ext = os.path.splitext(os.path.basename(str(src)))
		if ext not in ('.c', '.cpp'):
			raise ValueError("Unknown extension: {}".format(ext))
		self.objects += self.env.Object(self.build_dir.File(base+'.o'), src)

	def sketch(self, sketch):
		self.add_generator(self._find_sources(self.src_dir))
		elf = self.env.Program(sketch+'.elf', self.objects)
		eep = self.env.Command(sketch+'.eep', elf, '$OBJCOPY -O ihex -j .eeprom --set-section-flags=.eeprom=alloc,load --no-change-warnings --change-section-lma .eeprom=0 $SOURCE $TARGET')
		hex = self.env.Command(sketch+'.hex', elf, '$OBJCOPY -O ihex -R .eeprom $SOURCE $TARGET')
		print self.env['OBJCOPY']
		self.env.Default(hex, eep)
		self.env.Alias('upload', self.env.Command(None, hex, self.upload_command()))
