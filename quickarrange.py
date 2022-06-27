import os
import numpy as np

import audio as a
import beatgen as bg

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

tempo_gen, has_kick_gen, drum_gens = bg.prep_beat(".")

if drum_randomness != "random":
	bpm = int(bpm)
	bass_name = "drums/808/808 [Spinz].wav"
	kick_name = "drums/Kick/Kick [Clean].wav"
	snare_name = "drums/Snare/Snare [Choppy].wav"
	clap_name = "drums/Clap/Clap [Dark].wav"
	hat_name = "drums/Hi Hat/Hi Hat [Metro].wav"
	openhat_name = "drums/Open Hat/Open Hat [StoleYou].wav"
else:
	rng = np.random.default_rng()
	bpm = tempo_gen.choice()
	bass_name = "drums/808/" + rng.choice(os.listdir("drums/808"))
	kick_name = "drums/Kick/" + rng.choice(os.listdir("drums/Kick"))
	snare_name = "drums/Snare/" + rng.choice(os.listdir("drums/Snare"))
	clap_name = "drums/Clap/" + rng.choice(os.listdir("drums/Clap"))
	hat_name = "drums/Hi Hat/" + rng.choice(os.listdir("drums/Hi Hat"))
	openhat_name = "drums/Open Hat/" + rng.choice(os.listdir("drums/Open Hat"))

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

bass_pattern = a.Pattern(bpm, 8)
bass_pattern.place_hits(bass, bass_notes, cut = True)
kick_pattern = a.Pattern(bpm, 8)
kick_pattern.place_hits(kick, kick_notes)
snare_pattern = a.Pattern(bpm, 8)
snare_pattern.place_hits(snare, snare_notes)
clap_pattern = a.Pattern(bpm, 8)
clap_pattern.place_hits(clap, clap_notes)
openhat_pattern = a.Pattern(bpm, 8)
openhat_pattern.place_hits(openhat, openhat_notes)
hat_pattern = a.Pattern(bpm, 16)
i = 0
while i < len(hatroll_notes):
	repetitions = int(hatroll_notes[i])
	if repetitions == 0:
		hat_pattern.place(hat, i / 2 + 1)
		i += 1
	elif repetitions in (2, 4, 6, 8):
		hat_pattern.roll(hat, i / 2 + 1, repetitions // 2, 1 / repetitions)
		i += 1
	elif repetitions == 3:
		hat_pattern.roll(hat, i / 2 + 1, repetitions, 1 / repetitions)
		i += 2

song = a.Pattern(bpm, 8)
song += bass_pattern + kick_pattern + snare_pattern + clap_pattern + hat_pattern + openhat_pattern
song.fade(start_index = len(song) - 200)
song.soft_clip()
song.repeat(2)
song.play()
