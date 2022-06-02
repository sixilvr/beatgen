#TODO: soft clip iso. distort at end, possibility of no kick, metro double kick, based bpm, depends if reverse melody, make api, update random to default_rng

import os
import random

import numpy as np
from scipy import interpolate, signal

import audio as a

SEED = random.getrandbits(32)
print("Seed:", SEED)
random.seed(SEED)

def chance(probability, true_value = 60, false_value = 0):
    return true_value if random.random() <= probability else false_value

def random_pdf(pdf_dict):
    return np.random.choice(list(pdf_dict.keys()), p = list(pdf_dict.values()))

def get_note_scale(root_midi):
    return np.array([0, 2, 3, 5, 7, 8, 12]) + root_midi

def get_arpeggio(scale, num_notes = 8, interval = 2):
    out = [0 for _ in range(num_notes)]
    beat_index = 0
    note_index = 0
    while beat_index < num_notes:
        out[beat_index] = scale[note_index % len(scale)]
        beat_index += interval
        note_index += random.choice([-1, 1])
    return out

def get_arpeggio(scale, num_notes = 8):
    interval = random.choice([1, 2, 2, 2, 4, 4])
    out = [0 for _ in range(num_notes)]
    beat_index = 0
    note_index = random.choice([0, 4])
    while beat_index < num_notes:
        out[beat_index] = scale[note_index]
        note_index = (note_index + random.choice([-3, -1, 2, 3, 4])) % len(scale)
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
    arp_name = random.choice(os.listdir(arp_path))
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
    bass_name = random.choice(os.listdir(os.path.join(drum_path, "808")))
    bass_sound = a.Sound(file = os.path.join(drum_path, "808", bass_name))
    if bass_sound.seconds > 4:
        bass_sound.resize(4 * 44100)
    bass_sound.normalize(a.db_to_amplitude(-8))
    bass_sound.fade()
    bass_root = restrict_midi(
        a.frequency_to_midi(a.nearest_note_frequency(bass_sound.fundamental)), 55, 67)

    kick_name = random.choice(os.listdir(os.path.join(drum_path, "Kick")))
    kick_sound = a.Sound(file = os.path.join(drum_path, "Kick", kick_name))
    kick_sound.normalize(a.db_to_amplitude(-7))

    snare_name = random.choice(os.listdir(os.path.join(drum_path, "Snare")))
    snare_sound = a.Sound(file = os.path.join(drum_path, "Snare", snare_name))
    snare_sound.normalize(a.db_to_amplitude(-6))
    """
    counter_snare_name = random.choice(os.listdir(os.path.join(drum_path, "Snare")))
    counter_snare_sound = a.Sound(file = os.path.join(drum_path, "Snare", counter_snare_name))
    counter_snare_sound.normalize(a.db_to_amplitude(-6))
    """
    clap_name = random.choice(os.listdir(os.path.join(drum_path, "Clap")))
    clap_sound = a.Sound(file = os.path.join(drum_path, "Clap", clap_name))
    clap_sound.normalize(a.db_to_amplitude(-6))

    hat_name = random.choice(os.listdir(os.path.join(drum_path, "Hi Hat")))
    hat_sound = a.Sound(file = os.path.join(drum_path, "Hi Hat", hat_name))
    hat_sound.normalize(a.db_to_amplitude(-15))

    openhat_name = random.choice(os.listdir(os.path.join(drum_path, "Open Hat")))
    openhat_sound = a.Sound(file = os.path.join(drum_path, "Open Hat", openhat_name))
    openhat_sound.normalize(a.db_to_amplitude(-16))

    return ((bass_name, bass_sound, bass_root),
        (kick_name, kick_sound),
        (snare_name, snare_sound),
        #(counter_snare_name, counter_snare_sound),
        (clap_name, clap_sound),
        (hat_name, hat_sound),
        (openhat_name, openhat_sound))

def read_song_data(data_file):
    """
    # Data File Format:
    song name
    tempo
    bass pattern
    kick pattern
    snare pattern
    clap pattern
    hat roll pattern
    open hat pattern
    # song name is not used by code
    # all patterns are 16 characters, either "1" or "0", except for hat roll, which can be "3", "4", "6", or "8"
    # each song entry is separated by 2 newlines
    # no newlines at the start or end of the file
    """

    with open(data_file, "rt") as f:
        data = f.read()
    songs = data.split("\n\n")
    num_songs = len(songs)

    patterns = {}
    patterns["bass"] = np.zeros((num_songs, 16))
    patterns["kick"] = np.zeros((num_songs, 16))
    patterns["snare"] = np.zeros((num_songs, 16))
    patterns["clap"] = np.zeros((num_songs, 16))
    patterns["hatroll"] = np.zeros((num_songs, 16))
    patterns["openhat"] = np.zeros((num_songs, 16))
    tempos = np.zeros(num_songs)
    no_kick_count = 0
    bass_or_kick = {
        "bass": 0,
        "kick": 0
    }
    snare_or_clap = {
        "both": 0,
        "snare": 0,
        "clap": 0
    }
    hatroll_amounts = np.array([])

    def parse_pattern(pattern):
        return np.array([int(beat) for beat in pattern])

    for i, song in enumerate(songs):
        name, tempo, bass, kick, snare, clap, hatroll, openhat = song.split("\n")

        patterns["bass"][i] = parse_pattern(bass)
        patterns["kick"][i] = parse_pattern(kick)
        patterns["snare"][i] = parse_pattern(snare)
        patterns["clap"][i] = parse_pattern(clap)
        hatroll_pattern = parse_pattern(hatroll)
        patterns["hatroll"][i] = np.array([1 if beat else 0 for beat in hatroll_pattern])
        patterns["openhat"][i] = parse_pattern(openhat)

        tempos[i] = int(tempo)

        if "1" not in kick:
            no_kick_count += 1
        else:
            for i in range(16):
                if kick[i] == "1":
                    bass_or_kick["kick"] += 1
                if bass[i] == "1":
                    bass_or_kick["bass"] += 1

        if "1" in snare and "1" in clap:
            snare_or_clap["both"] += 1
        elif "1" in snare and not "1" in clap:
            snare_or_clap["snare"] += 1
        elif "1" not in snare and "1" in clap:
            snare_or_clap["clap"] += 1

        hatroll_amounts = np.append(hatroll_amounts, np.extract(hatroll_pattern != 0, hatroll_pattern))

    drum_averages = {}
    drum_averages["bass"] = np.mean(patterns["bass"], 0)
    drum_averages["kick"] = np.mean(patterns["kick"], 0)
    drum_averages["snare"] = np.mean(patterns["snare"], 0)
    drum_averages["clap"] = np.mean(patterns["clap"], 0)
    drum_averages["hatroll"] = np.mean(patterns["hatroll"], 0)
    drum_averages["openhat"] = np.mean(patterns["openhat"], 0)

    tempos.sort()
    tempos, tempo_frequencies = np.unique(tempos, return_counts = True)
    tempo_pdf = interpolate.interp1d(tempos, tempo_frequencies, assume_sorted = True)
    tempos = np.arange(min(tempos), max(tempos) + 1)
    tempo_frequencies = tempo_pdf(tempos)
    tempo_frequencies = signal.convolve(tempo_frequencies, np.ones(5) / 5, mode = "same")
    tempo_frequencies /= sum(tempo_frequencies)

    no_kick_rate = no_kick_count / len(songs)

    bass_or_kick_total = sum(bass_or_kick.values())
    bass_or_kick["bass"] /= bass_or_kick_total
    bass_or_kick["kick"] /= bass_or_kick_total

    snare_or_clap_total = sum(snare_or_clap.values())
    snare_or_clap["both"] /= snare_or_clap_total
    snare_or_clap["snare"] /= snare_or_clap_total
    snare_or_clap["clap"] /= snare_or_clap_total

    hatroll_amounts.sort()
    hatroll_amounts, hatroll_frequencies = np.unique(hatroll_amounts, return_counts = True)
    hatroll_amounts = hatroll_amounts.astype(int)
    hatroll_frequencies = hatroll_frequencies.astype(float)
    hatroll_frequencies /= sum(hatroll_frequencies)

    return (drum_averages,
        (tempos, tempo_frequencies),
        no_kick_rate,
        bass_or_kick,
        snare_or_clap,
        (hatroll_amounts, hatroll_frequencies))

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

def get_kick_bass_notes(kick_sound, bass_sound, bass_root, kick_probabilities, bass_probabilities, bass_or_kick, melody_notes):
    def get_last_note(pattern, index):
        while pattern[index] == 0:
            index -= 1
        return pattern[index]
    repetitions = len(melody_notes) // 16
    kick_notes = [0 for _ in range(len(melody_notes))]
    bass_notes = [0 for _ in range(len(melody_notes))]
    for i, probability in enumerate(np.tile((kick_probabilities + bass_probabilities) / 2, 2)):
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