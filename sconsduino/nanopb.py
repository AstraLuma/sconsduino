"""
Module to work with the NanoPB library.

Why? Because I use it.
"""
import os.path


"""
Example:
from sconsduino.teensy import Teensy
from sconsduino.nanopb import NanoPB
env = Environment()
npb = NanoPB(env=env, build_dir='bin')

npb.add("protocols/server.proto")

teensy = Teensy(
	version=3.1,
	env=env,
	build_dir='bin',
)

teensy.libs("wire", "CC3000")
teensy.cpu(speed=96000000)
teensy.layout('US_ENGLISH')
teensy.add_generator(npb)
teensy.sketch('blinky')
"""

class NanoPB(object):
	build_dir = None
	def __init__(self, env, build_dir=None):
		self.env = env
		self.build_dir = self.env.Dir(build_dir or '.')
		self.env.Append(
			PROTOC='protoc',
			NANOPB=self._findnano(),
			CPPPATH=['$NANOPB'],
			#PROTOPATH='-Iprotocols',
		)
		# Variables have to be in place before Builder() is called.
		self.env.Append(
			BUILDERS={
				'Proto': self.env.Builder(
					action='$PROTOC --plugin=protoc-gen-nanopb=$NANOPB/generator/protoc-gen-nanopb --nanopb_out={} $PROTOPATH $$SOURCE'
						.format(self.build_dir.get_abspath()),
					#suffix=['.pb.c', '.pb.h'],
					src_suffix='.proto',
					),
			}
		)
		self.objects = []

	def _findnano(self):
		usrpath = os.path.expanduser("~/.local/nanopb")
		syspath = "/usr/local/share/nanopb"
		if os.path.exists(usrpath):
			return usrpath
		else:
			return syspath

	def add(self, src):
		src = self.env.File(src)
		fn = str(src)
		b, e = os.path.splitext(fn)
		cdest = self.build_dir.File(b+'.pb.c')
		hdest = self.build_dir.File(b+'.pb.h')
		p = self.env.Proto([cdest, hdest], src)
		self.objects += [o for o in p if str(o).endswith('.c')]
		self.env.Append(
			CPPPATH=[hdest.get_dir()]
		)

	def __iter__(self):
		yield self.env.File("$NANOPB/pb_encode.c")
		yield self.env.File("$NANOPB/pb_decode.c")
		yield self.env.File("$NANOPB/pb_common.c")
		for o in self.objects:
			yield o
