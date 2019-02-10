from setuptools import setup
from tesliper import tesliper

with open("README", 'r') as readme:
    long_desc = readme.read()

setup(
    name='tesliper',
    version=tesliper.__version__,
    description="package for batch processing of Gaussian output files "
                "with spectral data",
    author=tesliper.__author__,
    author_email="wieclawmm@gmail.com",
    url="https://github.com/Mishioo/tesliper",
    packages=['tesliper'],
    install_requires=['numpy', 'openpyxl'],
    scripts=['bin/start_gui.py', 'bin/runtests.py'],
    package_data={'tesliper': ['tesliper.ico']}
)
