import distutils.cmd
import subprocess
from distutils.util import convert_path

from setuptools import find_packages, setup

# bypass importing `tesliper`'s content to avoid ImportError
# approach suggested by https://stackoverflow.com/a/24517154/11416569
metadata = {}
md_path = convert_path("tesliper/_metadata.py")
with open(md_path) as md_file:
    exec(md_file.read(), metadata)  # load variables into dict


class BuildBinaryCommand(distutils.cmd.Command):
    description = "build standalone binary file for Windows"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        command = [
            "pyinstaller",
            "--noconfirm",
            "--onefile",
            "--icon",
            ".\\tesliper\\tesliper.ico",
            "--name",
            "Tesliper",
            "--paths",
            ".",
            "--add-data",
            ".\\tesliper\\tesliper.ico;tesliper",
            "--noconsole",
            ".\\bin\\tesliper_gui.py",
        ]
        subprocess.run(command)


with open("README.md", "r") as readme:
    long_desc = readme.read()

extras_require = {
    "gui": ["matplotlib"],
    "test": ["pytest", "hypothesis", "coverage", "pytest-cov"],
    "docs": ["sphinx", "sphinx-rtd-theme"],
    "build": ["pyinstaller", "twine"],
    "dev": ["black", "pre-commit", "flake8", "isort"],
}
extras_require["dev-all"] = sum(extras_require.values(), [])
extras_require["build"] += extras_require["gui"]
extras_require["dev"] += extras_require["gui"] + extras_require["test"]


setup(
    cmdclass={"binary": BuildBinaryCommand},
    name="tesliper",
    version=metadata["__version__"],
    description=(
        "a package for batch processing of spectra-related Gaussian output files"
    ),
    long_description=long_desc,
    long_description_content_type="text/markdown",
    author=metadata["__author__"],
    author_email="wieclawmm@gmail.com",
    url="https://github.com/mishioo/tesliper",
    packages=find_packages(),
    install_requires=["numpy", "openpyxl"],
    extras_require=extras_require,
    python_requires=">=3.6",
    scripts=["bin/tesliper_gui.py"],
    entry_points={"console_scripts": ["tesliper-gui=tesliper.gui:run"]},
    package_data={"tesliper": ["tesliper.ico"]},
    classifiers=[
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Development Status :: 4 - Beta",
    ],
    keywords=[
        "chemistry",
        "chemical computing",
        "optical spectroscopy",
        "spectral simulations",
        "spectroscopy",
        "Gaussian",
        "workflow automation",
        "batch processing",
    ],
)
