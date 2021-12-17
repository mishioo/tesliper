"""Classes for reading and parsing files.

Abstract Base Class for parsers, as well as concrete parser implementations are defined
in this subpackage. It also contains a :class:`.Soxhlet` class that is designed to
orchestrate batch data extraction.
"""
from .base_parser import Parser
from .gaussian_parser import GaussianParser
from .parameters_parser import ParametersParser
from .soxhlet import Soxhlet
from .spectra_parser import SpectraParser
