import numpy as np
from scipy import interpolate

class RandomSelector:
    def __init__(self):
        self.data = {}
        self.total_inputs = 0

    def __repr__(self):
        return f"randomselectors.RandomSelector()"

    def add_data(self, key):
        if key not in self.data:
            self.data[key] = 1
        else:
            self.data[key] += 1
        self.total_inputs += 1
    
    def choice(self, rng):
        return rng.choice(list(self.data.keys()),
            p = [i / self.total_inputs for i in self.data.values()])

class RandomPattern:
    def __init__(self, beats = 8, step_size = 0.5):
        self.beats = beats
        self.step_size = step_size
        self.selectors = [RandomSelector() for _ in range(int(self.beats / self.step_size))]

    def __repr__(self):
        return f"randomselectors.RandomPattern(beats = {self.beats}, step_size = {self.step_size})"

    def add_data(self, beat, key):
        selector = self.selectors[int(beat / self.step_size) - 1]
        selector.add_data(key)

    def read_pattern(self, pattern):
        if len(pattern) != int(self.beats / self.step_size):
            raise ValueError(f"Pattern length must be {int(self.beats / self.step_size)}, got {len(pattern)}")
        for i, char in enumerate(pattern):
            self.selectors[i].add_data(int(char))

    def read_two_patterns(self, pattern1, pattern2):
        """
        0: neither
        1: pattern1
        2: pattern2
        3: both
        """
        for i, chars in enumerate(zip(pattern1, pattern2)):
            match chars:
                case ("0", "0"):
                    value = 0
                case ("1", "0"):
                    value = 1
                case ("0", "1"):
                    value = 2
                case ("1", "1"):
                    value = 3
            self.selectors[i].add_data(value)

    def random_value(self, beat, rng):
        selector = self.selectors[int(beat / self.step_size) - 1]
        return selector.choice(rng)

    def generate_pattern(self, rng, repetitions = 1):
        out = ""
        for selector in self.selectors * repetitions:
            out += str(selector.choice(rng))
        return out

    def generate_two_patterns(self, rng, repetitions = 1):
        out1 = ""
        out2 = ""
        for selector in self.selectors * repetitions:
            value = selector.choice(rng)
            match value:
                case 0:
                    out1 += "0"
                    out2 += "0"
                case 1:
                    out1 += "1"
                    out2 += "0"
                case 2:
                    out1 += "0"
                    out2 += "1"
                case 3:
                    out1 += "1"
                    out2 += "1"
                case other:
                    raise ValueError(f"{other} was used found when generating two patterns. Only (0, 1, 2, 3) are allowed")
        return out1, out2

class ContinuousRandomSelector(RandomSelector):
    def __init__(self):
        super().__init__()

    def __repr__(self):
        return f"randomselectors.ContinuousRandomSelector()"

    def choice(self, rng):
        keys = list(self.data.keys())
        values = list(self.data.values())
        interpf = interpolate.interp1d(keys, values)
        new_keys = np.arange(min(keys), max(keys) + 1)
        new_values = interpf(new_keys)
        new_values /= sum(new_values)
        return rng.choice(new_keys, p = new_values)
