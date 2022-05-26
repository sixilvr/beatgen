import os
import random

import audio as a

"""
title/randomness
bpm
808
kick
snare
clap
hat rolls
open hat
"""

beat_data = """
not random
124
1000001000100000
1001001000100101
0000000101000000
0000100000001000
4000000000000000
0000000000000000
""".strip()

drum_randomness, bpm, bass_notes, kick_notes, snare_notes, clap_notes, hatroll_notes, openhat_notes = beat_data.split("\n")

if drum_randomness != "random":
	bass_name = "drums/808/808 [Spinz].wav"
	kick_name = "drums/Kick/Kick [Clean].wav"
	snare_name = "drums/Snare/Snare [Choppy].wav"
	clap_name = "drums/Clap/Clap [Dark].wav"
	hat_name = "drums/Hi Hat/Hi Hat [Metro].wav"
	openhat_name = "drums/Open Hat/Open Hat [StoleYou].wav"
else:
	bpm = random.randint(125, 150)
	bass_name = "drums/808/" + random.choice(os.listdir("drums/808"))
	kick_name = "drums/Kick/" + random.choice(os.listdir("drums/Kick"))
	snare_name = "drums/Snare/" + random.choice(os.listdir("drums/Snare"))
	clap_name = "drums/Clap/" + random.choice(os.listdir("drums/Clap"))
	hat_name = "drums/Hi Hat/" + random.choice(os.listdir("drums/Hi Hat"))
	openhat_name = "drums/Open Hat/" + random.choice(os.listdir("drums/Open Hat"))

print(bpm)
print(bass_name)
print(kick_name)
print(snare_name)
print(clap_name)
print(hat_name)
print(openhat_name)

kick = a.Sound(file = kick_name)
kick.normalize(0.5)
bass = a.Sound(file = bass_name)
bass.normalize(0.5)
snare = a.Sound(file = snare_name)
snare.normalize(0.5)
clap = a.Sound(file = clap_name)
clap.normalize(0.5)
hat = a.Sound(file = hat_name)
hat.normalize(0.3)
openhat = a.Sound(file = openhat_name)
openhat.normalize(0.2)

song = a.Pattern(int(bpm), 8)

song.place_pattern(bass, ["C4" if i == "1" else 0 for i in bass_notes], cut = True)
song.place_pattern(kick, ["C4" if i == "1" else 0 for i in kick_notes])
song.place_pattern(openhat, ["C4" if i == "1" else 0 for i in openhat_notes])
song.place_pattern(snare, ["C4" if i == "1" else 0 for i in snare_notes])
song.place_pattern(clap, ["C4" if i == "1" else 0 for i in clap_notes])
song.roll(hat, 1, 16, 0.5)
for beat in range(16):
	if hatroll_notes[beat] != "0":
		rollperbeat = random.choice([2, 3, 4, 6])
		song.roll(hat, beat / 2 + 1, rollperbeat, 0.5 / rollperbeat, 0.5)

song.fade(start_index = song.length - 200)
song.distort()
song.repeat(2)
song.play()
