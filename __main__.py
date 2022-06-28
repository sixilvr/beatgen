import os
import pprint

from . import beatgen

data = beatgen.generate_beat("test.wav", os.path.dirname(__file__), play = True)
pprint.pprint(data)
