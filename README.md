[![Build status](https://ci.appveyor.com/api/projects/status/vh0t6udj7mnpnfoe?svg=true)](https://ci.appveyor.com/project/mishioo/tesliper-jjshl)
[![Documentation Status](https://readthedocs.org/projects/tesliper/badge/?version=stable)](https://tesliper.readthedocs.io/en/stable/?badge=stable)
[![Coverage Status](https://coveralls.io/repos/github/mishioo/tesliper/badge.svg)](https://coveralls.io/github/mishioo/tesliper)
[![PyPi version](https://badgen.net/pypi/v/tesliper/)](https://pypi.org/project/tesliper)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/tesliper.svg)](https://pypi.python.org/pypi/tesliper/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License](https://img.shields.io/badge/License-BSD_2--Clause-orange.svg)](https://opensource.org/licenses/BSD-2-Clause)

<img align="right" width="100" height="100" src="https://raw.githubusercontent.com/mishioo/tesliper/master/tesliper/tesliper.ico">

# Tesliper

Tesliper: Theoretical Spectroscopist Little Helper is a program for batch processing
of Gaussian output files. It is focused on calculation of vibrational, electronic, and
scattering spectra from Gaussian-calculated quantum properties of molecule conformers.
Please note, that this project is still under developenemt, thus it may be prone to errors.
Tesliper is written in Python 3.6 and makes use of some additional third party packages
(see below or requirements.txt). It may be used as a package or as a stand-alone
application with dedicated GUI.

- [Tesliper](#tesliper)
- [Getting Started](#getting-started)
  - [Requirements](#requirements)
  - [Installing to your Python distribution](#installing-to-your-python-distribution)
  - [A standalone application](#a-standalone-application)
- [Documentation](#documentation)
  - [Primer](#primer)
  - [Using in Python scripts](#using-in-python-scripts)
  - [Using a graphical interface](#using-a-graphical-interface)
- [License](#license)
- [Contributing to Tesliper](#contributing-to-tesliper)
  - [Bugs and suggestions](#bugs-and-suggestions)
  - [Participating in code](#participating-in-code)

# Getting Started

You can use Tesliper from python or as standalone application with dedicated graphical user inteface. See below for details.

## Requirements

```
Python 3.6+
numpy
openpyxl
matplotlib (needed only for gui)
```
This package is written in Python 3.6. and will not work with any previous release.

## Installing to your Python distribution

Tesliper is available on PyPI, you can install it to your python distribution by simply running:

`> python -m pip install tesliper`

or

`> python -m pip install tesliper[gui]`

if you would like to be able to use a graphical interface.

## A standalone application

This option is currently available only for Windows users.
To get your copy of Tesliper, simply download an .exe file from
[latest relase](https://github.com/Mishioo/tesliper/releases/latest).
This file is a standalone application, no installation is required.

# Documentation
Full documentation is available online: https://tesliper.readthedocs.io/.

## Primer
`tesliper` is designed to work with multiple conformers of a compound,
represented by a number of files obtained from Gaussian quantum-chemical
computations software. It allows to easily exclude conformers that are not suitable
for further analysis: erroneous, not optimized, of higher energy or lower contribution
than a user-given threshold. It also implements an RMSD sieve,
enabling one to filter out similar structures.
Finally, it lets you calculate theoretical IR, VCD, UV, ECD, Raman, and ROA spectra
for all conformers or as a population-weighted average and export obtained spectral
data in one of supported file formats: `.txt`, `.csv`, or `.xlsx`.

There are some conventions that are important to note:
- `tesliper` stores multiple data entries of various types for each conformer.
To prevent confusion with Python's data ``type`` and with data itself,
`tesliper` refers to specific kinds of data as "genres". Genres in code are represented
by specific strings, used as identifiers. To learn about data genres
known to `tesliper`, see [Available data genres](https://tesliper.readthedocs.io/)
section, which lists them. <!-- TODO link correct docs section -->
- `tesliper` identifies conformers using a stem of an extracted file (i.e. its filename
without extension). When files with identical names are extracted in course of
subsequent `Tesliper.extract` calls or in recursive extraction using
``Tesliper.extract(recursive=True)``, they are treated as data for one conformer.
This enables to join data from subsequent calculations steps, e.g. geometry
optimization, vibrational spectra simulation, and electronic spectra simulation.
Please note that if specific data genre is available from more than one calculation
job, only recently extracted values will be stored.
- `tesliper` was designed to deal with multiple conformers of single molecule and may
not work properly when used to process data concerning different molecules (i.e.
having different number of atoms, different number of degrees of freedom, etc.).
If you want to use it for such purpose anyway, you may set
`Tesliper.conformers.allow_data_inconsistency` to ``True``. `tesliper` will then stop
complaining and try to do its best.

## Using in Python scripts
`Tesliper` class is the main access point to `tesliper`'s functionality. It allows you
to extract data from specified files, provides a proxy to the trimming
functionality, gives access to data in form of specialized arrays, enables you
to calculate and average desired spectra, and provides an easy way to export data.

Most basic use might look like this:
```
>>> from tesliper import Tesliper
>>> tslr = Tesliper()
>>> tslr.extract()
>>> tslr.calculate_spectra()
>>> tslr.average_spectra()
>>> tslr.export_averaged()
```
This extracts data from files in the current working directory, calculates
available spectra using standard parameters, averages them using available energy
values, and exports to current working directory in .txt format.

You can customize this process by specifying call parameters for used methods
and modifying `Tesliper`'s configuration attributes:
- to change source directory
or location of exported files instantiate `Tesliper` object with `input_dir`
and `output_dir` parameters specified, respectively. You can also set appropriate
attributes on the instance directly.
- To extract only selected files in `input_dir` use `wanted_files` init parameter.
It should be given an iterable of filenames you want to parse. Again, you can
also directly set an identically named attribute.
- To change parameters used for calculation of spectra, modify appropriate entries
of `parameters` attribute.
- Use other export methods to export more data and specify `fmt` parameter
in method's call to export to other file formats.

```
>>> tslr = Tesliper(input_dir="./myjob/optimization/", output_dir="./myjob/output/")
>>> tslr.wanted_files = ["one", "two", "three"]  # only files with these names
>>> tslr.extract()  # use tslr.input_dir as source
>>> tslr.extract(path="./myjob/vcd_sim/")  # use other input_dir
>>> tslr.conformers.trim_not_optimized()  # trimming out unwanted conformers
>>> tslr.parameters["vcd"].update({"start": 500, "stop": 2500, "width": 2})
>>> tslr.calculate_spectra(genres=["vcd"])  # we want only VCD spectrum
>>> tslr.average_spectra()
>>> tslr.export_averaged(mode="w")  # overwrite previously exported files
>>> tslr.export_activities(fmt="csv")  # save activities for analysis elsewhere
>>> tslr.output_dir = "./myjob/ecd_sim/"
>>> tslr.export_job_file(  # prepare files for next step of calculations
...     route="# td=(singlets,nstates=80) B3LYP/Def2TZVP"
... )
```

## Using a graphical interface
If you are using `tesliper` as a standalone application, simply double click on the
`Tesliper.exe` file to start the application. To invoke it from the command line,
run `python -m tesliper.gui`. GUI consists of three panels and a number of controls.
The panels are: "Extracted data", "Energies list", and "Spectra view". First two
offer a list of conformers read so far using "Chose files" and "Chose folder" buttons
on the left. The last enables to preview calculated spectra.

- "Extracted data" panel shows an identifier of each conformer (a file name) and an
overview of data extracted. Little checkboxes on the left of each conformer may be
clicked to mark this conformer as "kept" or "not kept".
- "Energies list" offers the same set of conformers and checkboxes, but with energies
values listed for each conformer. The view may be changed using "Show" dropdown box
in "Filter kept conformers" section of controls, to present difference in energy
between conformers or their percentage contribution in population.
- "Spectra view" tab shows calculated spectra. It may be controlled using "Calculate
spectra" section. After choosing a spectra genre to calculate you may control
if it is simulated using lorentzian or gaussian fitting function, change peak width,
spectra bounds, etc. You may view spectra for one conformer, all of them stacked,
or averaged. You may also load an experimental spectrum (.txt format) for comparison.

Once done with extracting files and tweaking parameters, export selected data to desired
format or save the session for later using buttons in "Session control" section.

# License
This project is licensed with BSD 2-Clause license.
See [LICENSE.txt](https://github.com/mishioo/tesliper/blob/master/LICENSE.txt)
file for details.

# Contributing to Tesliper
Contributions are welcome! `tesliper` is a growing project and definitely has room
for improvements. 

## Bugs and suggestions
Bug reports are of great value, if you encounter a problem please let me know by
submitting a [new issue](https://github.com/mishioo/tesliper/issues/new).
If you have a suggestion how `tesliper` can be improved, please let me know as well!

## Participating in code
If you'd like to contribute to `tesliper`'s codebase, that's even better!
If there is a specific bug that you know how to fix or a feature you'd like to develop,
please let me know via [issues](https://github.com/mishioo/tesliper/issues).
To get your change introduced to the codebase, please make a Pull Request to the
`fixes` branch for bug fixes or to the `dev` branch for new features.

If at a loss, do not hesitate to reach to me directly! :)
