import distutils.cmd
import subprocess

from setuptools import find_packages, setup

from tesliper import tesliper


class BuildBinaryCommand(distutils.cmd.Command):
    description = "build standalone binary file for Windows"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    # noinspection PyShadowingNames
    def run(self):
        command = [
            "pyinstaller",
            "-y",
            "-F",
            "-i",
            ".\\tesliper\\tesliper.ico",
            "-n",
            "Tesliper",
            "-p",
            ".",
            "--add-data",
            ".\\tesliper\\tesliper.ico;tesliper",
            "-w",
            ".\\bin\\tesliper_gui.py",
        ]
        subprocess.run(command)


with open("README.md", "r") as readme:
    long_desc = readme.read()

setup(
    cmdclass={"binary": BuildBinaryCommand},
    name="tesliper",
    version=tesliper.__version__,
    description="package for batch processing of Gaussian output files "
    "with spectral data",
    long_description=long_desc,
    author=tesliper.__author__,
    author_email="wieclawmm@gmail.com",
    url="https://github.com/mishioo/tesliper",
    packages=find_packages(),
    install_requires=["numpy", "openpyxl"],
    extras_require={"gui": ["matplotlib"]},
    scripts=["bin/tesliper_gui.py"],
    package_data={"tesliper": ["tesliper.ico"]},
)
