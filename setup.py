from distutils.core import setup

setup(name = "beatgen",
    version = "1.0",
    description = "A Python library for randomly generating music",
    author = "SL",
    url = "https://github.com/sixilvr/beatgen",
    packages = ["beatgen"],
    requires = ["audio @ git+https://github.com/sixilvr/audio", "numpy"]
)
