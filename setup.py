from setuptools import setup, find_packages
from tesliper import tesliper

with open("README", 'r') as readme:
    long_desc = readme.read()

setup(
    name='tesliper',
    version=tesliper.__version__,
    description="package for batch processing of Gaussian output files "
                "with spectral data",
    long_description=long_desc,
    author=tesliper.__author__,
    author_email="wieclawmm@gmail.com",
    url="https://github.com/Mishioo/tesliper",
    packages=find_packages(),
    install_requires=["numpy", "openpyxl"],
    extras_require={"gui": ["matplotlib"]},
    scripts=["bin/tesliper_gui.py"],
    package_data={"tesliper": ["tesliper.ico"]},
)
