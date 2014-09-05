sconsduino
==========

If you want to use Arduino libraries with a normal editor, this module may be for you.

Install this, and you can use an `SConstruct` file similar to:

```python
from sconsduino.teensy import Teensy

env = Environment()

board = Teensy(
	version=3.1,
	env=env,
	build_dir='bin',
)

# Set to 24000000, 48000000, or 96000000 to set CPU core speed
board.cpu(speed=96000000)

# (Teensy)
# For key layouts, set to US_ENGLISH, CANADIAN_FRENCH, CANADIAN_MULTILINGUAL, DANISH, FINNISH, FRENCH, FRENCH_BELGIAN, FRENCH_SWISS, 
# GERMAN, GERMAN_MAC, GERMAN_SWISS, ICELANDIC, IRISH, ITALIAN, NORWEGIAN, PORTUGUESE, PORTUGUESE_BRAZILIAN, SPANISH, SPANISH_LATIN_AMERICA, 
# SWEDISH, TURKISH, UNITED_KINGDOM, US_INTERNATIONAL
board.layout('US_ENGLISH')

# (Teensy)
board.usb_mode('SERIAL')

board.sketch('blinky')
```
