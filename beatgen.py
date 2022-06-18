#TODO: soft clip iso. distort at end, possibility of no kick, metro double kick, based bpm, depends if reverse melody, make api, update random to default_rng

import os
import random

import numpy as np
from scipy import interpolate, signal

import audio as a
import randomselectors as rs

SEED = random.getrandbits(32)
print("Seed:", SEED)
RNG = np.random.default_rng(SEED)

DRUM_NAMES = ("bass", "kick", "snare", "clap", "hatroll", "openhat")

def chance(probability, true_value = 60, false_value = 0):
    return true_value if RNG.random() <= probability else false_value

def random_pdf(pdf_dict):
    return RNG.choice(list(pdf_dict.keys()), p = list(pdf_dict.values()))

def get_note_scale(root_midi):
    return np.array([0, 2, 3, 5, 7, 8, 12]) + root_midi

def get_arpeggio(scale, num_notes = 8, interval = 2):
    out = [0 for _ in range(num_notes)]
    beat_index = 0
    note_index = 0
    while beat_index < num_notes:
        out[beat_index] = scale[note_index % len(scale)]
        beat_index += interval
        note_index += RNG.choice([-1, 1])
    return out

def get_arpeggio(scale, num_notes = 8):
    interval = RNG.choice([1, 2, 2, 2, 4, 4])
    out = [0 for _ in range(num_notes)]
    beat_index = 0
    note_index = RNG.choice([0, 4])
    while beat_index < num_notes:
        out[beat_index] = scale[note_index]
        note_index = (note_index + RNG.choice([-3, -1, 2, 3, 4])) % len(scale)
        beat_index += interval
    return out

def restrict_midi(midi, lower, upper):
    if abs(upper - lower) < 12:
        raise ValueError(f"Lower ({lower}) and upper ({upper}) must have a difference of at least 12")
    while True:
        if midi < lower:
            midi += 12
        elif midi > upper:
            midi -= 12
        else:
            break
    return midi

def get_arp_sound(arp_path, volume_db, max_seconds = 1):
    arp_name = RNG.choice(os.listdir(arp_path))
    arp_file = os.path.join(arp_path, arp_name)
    arp = a.Sound(file = arp_file)
    arp.trim_silence()
    arp.filter("hp", 400)
    arp.filter("lp", 1000, 1)
    if arp.seconds > max_seconds:
        arp.resize(int(max_seconds * 44100))
    arp.fade()
    arp.normalize(a.db_to_amplitude(volume_db))
    return arp, arp_name

def get_drum_sounds(drum_path):
    drums = {
        "bass": {
            "folder": "808",
            "volume": -8
        },
        "kick": {
            "folder": "Kick",
            "volume": -7
        },
        "snare": {
            "folder": "Snare",
            "volume": -6
        },
        "clap": {
            "folder": "Clap",
            "volume": -6
        },
        "hat": {
            "folder": "Hi Hat",
            "volume": -15
        },
        "openhat": {
            "folder": "Open Hat",
            "volume": -16
        }
    }

    for drum_data in drums.values():
        drum_data["filename"] = RNG.choice(os.listdir(os.path.join(drum_path, drum_data["folder"])))
        drum_data["sound"] = a.Sound(file = os.path.join(drum_path, drum_data["filename"]))
        drum_data["sound"].normalize(a.db_to_amplitude(drum_data["volume"]))

    bass_sound = drums["bass"]["sound"]
    if bass_sound.seconds > 4:
        bass_sound.resize(4 * 44100)
    bass_sound.fade()
    drums["bass"]["root"] = restrict_midi(
        a.frequency_to_midi(a.round_frequency(bass_sound.fundamental)), 55, 67)

    return drums

def read_song_data(data_file):
    r"""
    ## Data File Format:
    song name\
    tempo\
    bass pattern\
    kick pattern\
    snare pattern\
    clap pattern\
    hat roll pattern\
    open hat pattern
    - song name is not used by code
    - all patterns are 16 characters, either "1" or "0", except for hat roll, which can be "3", "4", "6", or "8"
    - each song entry is separated by 2 newlines
    - no newlines at the start or end of the file
    """

    with open(data_file, "rt") as f:
        data = f.read()
    songs = data.split("\n\n")
    
    tempos = rs.ContRandomSelector(RNG)
    has_kick = rs.RandomSelector(RNG)
    patterns = {name: rs.RandomPattern(8, 0.5, RNG) for name in 
        ("bass_or_kick", "only_bass", "snare_or_clap", "hatroll", "openhat")}

    for i, song in enumerate(songs):
        song_name, tempo, bass, kick, snare, clap, hatroll, openhat = song.split("\n")
        
        tempos.add_data(tempo)

        if "1" in kick:
            has_kick.add_data(1)
            patterns["bass_or_kick"].read_two_patterns(bass, kick)
        else:
            has_kick.add_data(0)
            patterns["only_bass"].read_pattern(bass)
        
        patterns["snare_or_clap"].read_two_patterns(snare, clap)
        patterns["hatroll"].read_pattern(hatroll)
        patterns["openhat"].read_pattern(openhat)

    return tempos, has_kick, patterns

def get_drum_pattern(sound, probabilities, bpm, repetitions = 2):
    out = a.Pattern(bpm, 8 * repetitions)
    for i, probability in enumerate(np.tile(probabilities, repetitions)):
        if chance(probability):
            out.place(sound, i / 2 + 1)
    return out

def get_snare_notes(snare_probabilities, clap_probabilities, repetitions = 2):
    primary_pattern = [0 for _ in range(16 * repetitions)]
    for i in range(repetitions):
        primary_pattern[16 * i + 4] = 60
        primary_pattern[16 * i + 12] = 60
    secondary_pattern = [60 if chance(probability) and (i % 16 not in (4, 12)) else 0 for i, probability in
        enumerate(np.tile(snare_probabilities + clap_probabilities, repetitions))]
    return primary_pattern, secondary_pattern

def get_kick_bass_notes(bass_root, kick_probabilities, bass_probabilities, bass_or_kick, melody_notes):
    def get_last_note(pattern, index):
        while pattern[index] == 0:
            index -= 1
        return pattern[index]
    repetitions = len(melody_notes) // 16
    kick_notes = [0 for _ in range(len(melody_notes))]
    bass_notes = [0 for _ in range(len(melody_notes))]
    for i, probability in enumerate(np.tile((kick_probabilities + bass_probabilities) / 2, repetitions)):
        if chance(probability) or i % 16 == 0:
            state = random_pdf(bass_or_kick)
            if (chance(bass_or_kick["kick"]) and (i % 16 not in (4, 12))) or i % 16 == 0:
                kick_notes[i] = 60
            if chance(bass_or_kick["bass"]) or i % 16 == 0:
                bass_notes[i] = restrict_midi(get_last_note(melody_notes, i), bass_root - 5, bass_root + 7)
    return kick_notes, bass_notes

def get_hat_pattern(hat_sound, hatroll_probabilities, hatroll_amounts, hatroll_frequencies, bpm, repetitions = 2):
    out = a.Pattern(bpm, 8 * repetitions)
    i = 0
    while i < 16 * repetitions:
        if chance(hatroll_probabilities[i % 16]):
            roll_amount = np.random.choice(hatroll_amounts, p = hatroll_frequencies)
            if roll_amount != 3:
                out.roll(hat_sound.stretch((random.uniform(0.8, 1) ** 0.5) if roll_amount != 4 else 1, False),
                    i / 2 + 1, roll_amount // 2, 1 / roll_amount)
                i += 1
            else:
                if i % 2 == 1:
                    continue
                out.roll(hat_sound.stretch(random.uniform(0.8, 1) ** 0.5, False),
                    i / 2 + 1, roll_amount, 1 / roll_amount)
                i += 2
        else:
            out.place(hat_sound, i / 2 + 1)
            i += 1
    return out

def get_arp_notes(scale, num_notes = 8, probability = 0.75):
    return [random.choice(scale) if chance(probability) or i == 0 else 0 for i in range(num_notes)]

"""
bpm = random.randint(125, 150)
root = random.randint(60 - 7, 60 + 5)
scale = np.array([0, 2, 3, 7, 8, 12]) + root
arp = get_arp(-17)
arp_notes = get_arpeggio(scale, 8) * 2
for i in range(8, 16):
    if chance(0.2):
        arp_notes[i] = random.choice(scale)
arp_notes[0] = root
arp_pattern = a.Pattern(bpm, 8)
arp_pattern.place_midi(arp, arp_notes)
arp_harmony = []
for i in range(16):
    new_note = random.choice(scale)
    if chance(0.3) and (abs(arp_notes[i] - new_note) not in [0, 1, 2]):
        arp_harmony.append(new_note)
    else:
        arp_harmony.append(0)
arp_pattern.place_midi(arp, arp_harmony, multiplier = 0.5)
arp_pattern.fade(start_index = arp_pattern.length - 200)
if chance(0.05):
    arp_pattern.reverse()
    arp_notes.reverse()
    arp_notes[0] = root
arp_pattern.repeat(2)

arp2 = get_arp(-17, 1.5)
arp2_interval = 12 if arp2.fundamental < 1000 else 12
arp_notes2 = []
for i in range(16):
    new_note = random.choice(scale)
    if chance(0.4) and (abs(arp_notes[i] - new_note) not in [1, 2]):
        arp_notes2.append(new_note + arp2_interval)
    else:
        arp_notes2.append(0)
arp_notes2[0] = root + arp2_interval
arp_pattern2 = a.Pattern(bpm, 16)
arp_pattern2.place_midi(arp2, arp_notes2 * 2)
arp_pattern2.fade(start_index = arp_pattern2.length - 200)

kickp, snarep, hatrollp, openhatp = read_data()

kick_notes = [0 for _ in range(32)]
bass_notes = [0 for _ in range(32)]
for i, prob in enumerate(np.tile(kickp, 2)):
    if chance(prob):
        if i % 8 not in [4, 12]:
            kick_notes[i] = 60 if chance(0.9) or i % 16 == 0 else 0
        bass_notes[i] = restrict_midi(arp_notes[i % 16], bassroot - 3, bassroot + 9) if chance(0.7) or i % 16 == 0 else 0

kick_pattern = a.Pattern(bpm, 16)
kick_pattern.place_midi(kick, kick_notes)

bass_pattern = a.Pattern(bpm, 16)
bass_pattern.place_midi(bass, bass_notes, cut = True, root_note = bassroot)
bass_pattern.fade(start_index = bass_pattern.length - 200)

primary_snare, secondary_snare = random.sample([snare, clap], 2)
secondary_volume = random.uniform(0.7, 1)
snare_pattern = a.Pattern(bpm, 16)
for i, prob in enumerate(np.tile(snarep, 2)):
    if i % 16 in [4, 12] and chance(prob):
        snare_pattern.place(primary_snare, i / 2 + 1)
    elif chance(prob):
        snare_pattern.place(secondary_snare if chance(0.9) else primary_snare, i / 2 + 1, secondary_volume)

hat_pattern = a.Pattern(bpm, 16)
i = 0
while i < 32:
    if chance(hatrollp[i % 16]):
        rolls_per_beat = random.choices([3, 4, 6, 8, 12], [0.3, 0.7, 1, 0.9, 0.2], k = 1)[0]
        if rolls_per_beat == 3 and i % 2 == 1:
            rolls_per_beat = random.choices([4, 6, 8, 12], [0.7, 1, 0.9, 0.2], k = 1)[0]
        hat_pattern.roll(hat.stretch(random.uniform(0.8, 1.0), False), i / 2 + 1, rolls_per_beat // (2 if rolls_per_beat != 3 else 1), 1 / rolls_per_beat)
        if rolls_per_beat == 3:
            i += 2
        else:
            i += 1
    else:
        hat_pattern.place(hat, i / 2 + 1)
        i += 1

if chance(0.2):
    hat_pattern_simple = a.Pattern(bpm, 16)
    hat_pattern_simple.roll(hat, 1, 32, 0.5)
else:
    hat_pattern_simple = hat_pattern

openhat_pattern = a.Pattern(bpm, 16)
openhat_pattern.place_midi(openhat, get_random_pattern(openhatp) * 2)

print(a.midi_to_note(root), bpm)

song = a.Arrangement(bpm, 32)
song.repeat_pattern(arp_pattern, 1, 16)
song.repeat_pattern(arp_pattern2, 17, 24)
song.repeat_pattern(arp_pattern, 17, 24, 0.75)
song.repeat_pattern(arp_pattern, 25, 32)
song.repeat_pattern(snare_pattern, 5, 32)
song.repeat_pattern(hat_pattern_simple, random.choice([5, 9]), 12)
song.place_pattern(hat_pattern_simple, 13, 14)
song.repeat_pattern(hat_pattern, 17, 32)
song.repeat_pattern(bass_pattern, random.choice([5, 9, 13]), 32)
song.repeat_pattern(kick_pattern, random.choice([5, 9, 13]), random.choice([20, 24]))
song.repeat_pattern(kick_pattern, 25, 32)
song.repeat_pattern(openhat_pattern, random.choice([9, 13]), 16)
song.repeat_pattern(openhat_pattern, 25, 32)

riser = a.Pattern(bpm, 8)
chord = a.chord(scale)
for i in range(3):
    riser.sawtooth(a.midi_to_frequency(root), 0.025)
riser.noise(0.8)
riser.fade(start_amp = 0, end_amp = 1, exponent = 5)
riser.filter("lp", 500)
riser.filter("hp", 1500, 1)
riser.normalize(0.2)
song.place(riser, 4 * 16 - 7)

if __name__ == '__main__':
    song.save("test.wav", clip = True)
    a.play_file("test.wav")
"""