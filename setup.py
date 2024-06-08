from distutils.core import setup

setup(name = "beatgen",
    version = "1.4",
    description = "A Python library for randomly generating music",
    author = "SL",
    url = "https://github.com/sixilvr/beatgen",
    packages = ["beatgen"],
    install_requires = ["audio", "numpy"],
    package_data = {"beatgen": ["*.txt", "drums/*/*", "instruments/*"]}
)
