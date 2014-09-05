import os.path

class NanoPB:
	build_dir = None
	def __init__(self, env, defs={}, build_dir=None):
		self.env = env
		print(env)
		self.env.Append(
			PROTOC='protoc',
			NANOPB=self._findnano(),
			CPPPATH=['$NANOPB'],
			CPPDEFINES=defs,
			PROTOPATH='-Iprotocols',
			BUILDERS={
				'Proto': self.env.Builder(action='$PROTOC --plugin=protoc-gen-nanopb=$NANOPB/generator/protoc-gen-nanopb --nanopb_out=. $PROTOPATH $SOURCE',
					#suffix=['.pb.c', '.pb.h'],
					src_suffix='.proto',
					),
			}
		)
		if build_dir is not None:
			self.build_dir = self.env.Dir(build_dir)
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
		fn = os.path.basename(str(src))
		b, e = os.path.splitext(fn)
		if self.build_dir:
			cdest = self.build_dir.File(b+'.pb.c')
			hdest = self.build_dir.File(b+'.pb.h')
		else:
			cdest = self.env.File(b+'.pb.c')
			hdest = self.env.File(b+'.pb.h')
		p = self.env.Proto([cdest, hdest], src)
		self.objects += [o for o in p if str(o).endswith('.c')]

	def __iter__(self):
		yield self.env.File("$NANOPB/pb_encode.c")
		yield self.env.File("$NANOPB/pb_decode.c")
		for o in self.objects:
			yield o
