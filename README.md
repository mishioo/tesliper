[![Build status](https://ci.appveyor.com/api/projects/status/vh0t6udj7mnpnfoe?svg=true)](https://ci.appveyor.com/project/mishioo/tesliper-jjshl)
[![Documentation Status](https://readthedocs.org/projects/tesliper/badge/?version=stable)](https://tesliper.readthedocs.io/en/stable/?badge=stable)
[![Coverage Status](https://coveralls.io/repos/github/mishioo/tesliper/badge.svg)](https://coveralls.io/github/mishioo/tesliper)
[![PyPi version](https://badgen.net/pypi/v/tesliper/)](https://pypi.org/project/tesliper)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/tesliper.svg)](https://pypi.python.org/pypi/tesliper/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License](https://img.shields.io/badge/License-BSD_2--Clause-orange.svg)](https://opensource.org/licenses/BSD-2-Clause)

<img align="right" width="100" height="100" src="https://raw.githubusercontent.com/mishioo/tesliper/master/tesliper/tesliper.ico">

# `tesliper`

`tesliper`: Theoretical Spectroscopist's Little Helper is a program for batch processing
of Gaussian output files, focused on calculations of vibrational, electronic, and
scattering spectra from Gaussian-calculated quantum properties of molecule's conformers.

It allows to easily exclude conformers that are not suitable for further analysis:
erroneous, not optimized, of higher energy or lower contribution than a user-given
threshold. It also implements an RMSD sieve, enabling one to filter out similar
structures. It lets you calculate theoretical IR, VCD, UV, ECD, Raman, and ROA spectra
for each conformer or as a population-weighted average and export obtained spectral data
in one of supported file formats: `.txt`, `.csv`, or `.xlsx`. Finally, if allows to
easily setup a next calculations step with batch export to `.gjf` Gaussian input files.

`tesliper` is written in Python 3.6 and makes use of some additional third party
packages (see below or requirements.txt). It may be used as a package or as a
stand-alone application with dedicated GUI.

- [`tesliper`](#tesliper)
- [Getting Started](#getting-started)
  - [Requirements](#requirements)
  - [Installing to your Python distribution](#installing-to-your-python-distribution)
  - [A standalone application](#a-standalone-application)
- [How to use](#how-to-use)
  - [Primer](#primer)
  - [In Python scripts](#in-python-scripts)
  - [A graphical interface](#a-graphical-interface)
- [License](#license)
- [Contributing to `tesliper`](#contributing-to-tesliper)
  - [Bugs and suggestions](#bugs-and-suggestions)
  - [Participating in code](#participating-in-code)
  - [Roadmap](#roadmap)
  - [Acknowledgements](#acknowledgements)

# Getting Started

You can use `tesliper` from python or as standalone application with dedicated graphical
user interface. See below for details.

## Requirements

```
Python 3.6+
numpy
openpyxl
matplotlib (optional, for GUI)
```

`tesliper` uses `tkinter` to deliver the graphical interface. It is included in
most Python distributions, but please be aware, that some might miss it. You will
need to install it manually in such case.

## Installing to your Python distribution

`tesliper` is available on PyPI, you can install it to your python distribution by
simply running:

`$ python -m pip install tesliper`

or

`$ python -m pip install tesliper[gui]`

if you would like to be able to use a graphical interface.

## A standalone application

This option is currently available only for Windows users.
To get your copy of `tesliper`, simply download a `Tesliper.exe` file from the
[latest relase](https://github.com/Mishioo/tesliper/releases/latest).
This file is a standalone application, no installation is required.

# How to use
Full documentation is available online: https://tesliper.readthedocs.io/.

## Primer
Conventions that are important to note:

- `tesliper` stores multiple data entries of various types for each conformer. To
prevent confusion with Python's data ``type`` and with data itself, `tesliper` refers to
specific kinds of data as "genres". Genres in code are represented by specific strings,
used as identifiers. To learn about data genres known to `tesliper`, see [Available data
genres](https://tesliper.readthedocs.io/en/stable/genres.html).
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

## In Python scripts
`Tesliper` class is the main access point to `tesliper`'s functionality. It allows you
to extract data from specified files, provides a proxy to the trimming
functionality, gives access to data in form of specialized arrays, enables you
to calculate and average desired spectra, and provides an easy way to export data.

Most basic use might look like this:
```python
from tesliper import Tesliper
tslr = Tesliper()
tslr.extract()
tslr.calculate_spectra()
tslr.average_spectra()
tslr.export_averaged()
```
This extracts data from files in the current working directory, calculates
available spectra using standard parameters, averages them using available energy
values, and exports to current working directory in .txt format.

You can customize this process by specifying call parameters for used methods
and modifying `Tesliper`'s configuration attributes:
- to change source directory
or location of exported files instantiate `Tesliper` object with `input_dir`
and `output_dir` parameters specified, respectively. You can also set appropriate
attributes on the instance directly;
- to extract only selected files in `input_dir` use `wanted_files` init parameter.
It should be given an iterable of filenames you want to parse. Again, you can
also directly set an identically named attribute;
- use `Tesliper.conformers.trim...` methods to easily filter out conformers you wish
to ignore in further analysis;
- to change parameters used for calculation of spectra, modify appropriate entries
of `parameters` attribute;
- use other export methods to export more data and specify `fmt` parameter
in method's call to export to other file formats.

```python
tslr = Tesliper(input_dir="./myjob/optimization/", output_dir="./myjob/output/")
tslr.wanted_files = ["one", "two", "three"]  # only files with these names
tslr.extract()  # use tslr.input_dir as source
tslr.extract(path="./myjob/vcd_sim/")  # use other input_dir
tslr.conformers.trim_not_optimized()  # filtering out unwanted conformers
tslr.parameters["vcd"].update({"start": 500, "stop": 2500, "width": 2})
tslr.calculate_spectra(genres=["vcd"])  # we want only VCD spectrum
tslr.average_spectra()
tslr.export_averaged(mode="w")  # overwrite previously exported files
tslr.export_activities(fmt="csv")  # save activities for analysis elsewhere
tslr.output_dir = "./myjob/ecd_sim/"
tslr.export_job_file(  # prepare files for next step of calculations
    route="# td=(singlets,nstates=80) B3LYP/Def2TZVP"
)
```

## A graphical interface
If you are using `tesliper` as a standalone application, simply double click on the
`Tesliper.exe` file to start the application. To invoke it from the command line,
just run `tesliper-gui`. GUI consists of three panels and a number of controls.
The panels are: "Extracted data", "Energies list", and "Spectra view". First two
offer a list of conformers read so far using "Chose files" and "Chose folder" buttons
on the left. The last enables to preview calculated spectra.

![screenshot](https://raw.githubusercontent.com/mishioo/tesliper/master/docs/source/_static/screenshots/16426974012.png)

- "Extracted data" panel shows an identifier of each conformer (a file name) and an
overview of data extracted. Little checkboxes on the left of each conformer may be
clicked to mark this conformer as "kept" or "not kept".
- "Energies list" offers the same set of conformers and checkboxes, but with energies
values listed for each conformer. The view may be changed using "Show" dropdown box
in "Energies and Structure" section of controls, to present difference in energy
between conformers or their percentage contribution in population.
- "Spectra view" tab shows calculated spectra. It may be controlled using "Calculate
spectra" section. After choosing a spectra genre to calculate you may control if it is
simulated using lorentzian or gaussian fitting function, change peak width, spectra
bounds, etc. You may view spectra for one conformer, all of them stacked, or averaged.
You may also load an experimental spectrum (.txt or .csv format) for comparison.

![screenshot](https://raw.githubusercontent.com/mishioo/tesliper/master/docs/source/_static/screenshots/16426984646.png)

Once done with extracting files and tweaking parameters, export selected data to desired
format or save the session for later using buttons in "Session control" section.

A detailed tutorial with screenshots is available in the documentation:
https://tesliper.readthedocs.io/en/stable/gui.html.

# License
This project is licensed with BSD 2-Clause license.
See [LICENSE.txt](https://github.com/mishioo/tesliper/blob/master/LICENSE.txt)
file for details.

# Contributing to `tesliper`
Contributions are welcome! `tesliper` is a growing project and definitely has room
for improvements. 

## Bugs and suggestions
Bug reports are of great value, if you encounter a problem please let me know by
submitting a [new issue](https://github.com/mishioo/tesliper/issues/new).
If you have a suggestion how `tesliper` can be improved, please let me know as well!

## Participating in code
If you'd like to contribute to `tesliper`'s codebase, that's even better! If there is a
specific bug that you know how to fix or a feature you'd like to develop, please let me
know via [issues](https://github.com/mishioo/tesliper/issues). To start coding, get your
working copy of `tesliper`'s source code by cloning the repository and then setup your
environment by installing development dependencies (probably to a virtual environment):
```
python -m pip install .[dev]
```
Please remember to add/update relevant tests along with your code changes.
Make sure the test suite passes by running
```
python -m pytest test
```
To get your change introduced to the codebase, please make a Pull Request to the
`fixes` branch for bug fixes or to the `dev` branch for new features.

`tesliper`'s codebase is formatted with [`black`](https://black.readthedocs.io/) and
[`isort`](https://pycqa.github.io/isort/), please use these tools before issuing a Pull
Request. If you prefer to not need to remember about it, you may use a pre-commit
configuration available in this repository. To include it in your workflow, simply run
`pre-commit install` in your copy's root directory. Note, that this configuration
also sets up [`flake8`](https://flake8.pycqa.org/) linter.

If at a loss, do not hesitate to reach to me directly! :)

## Roadmap
Ideas for possible future improvements to the software are listed below. Based on the
feedback from the Community, I will decide, which ones are desired and worth working on.

### New Functionality: <!-- omit in toc -->
- command line interface
- support for Jaguar & other packages
- option for using `cclib` for parsing
- spectra comparison feature
- velocity and length electronic spectra comparison
- parsing conformational search files
- GUI: manually choose spectra colour

### UX Improvements: <!-- omit in toc -->
- supplement logging
- auto finding optimal spectra range
- GUI: export spectra as image
- GUI: spectra colour by population
- GUI: drag&drop support
- GUI: display tooltips on hover


## Acknowledgements

Many thanks to the scientists, who advised me on the domain-specific details and helped
to test the software:

[orcid_logo]: https://info.orcid.org/wp-content/uploads/2019/11/orcid_16x16.png

- Joanna Rode [![orcid_id][orcid_logo] 0000-0003-0592-4053](https://orcid.org/0000-0003-0592-4053)
- Magdalena Jawiczuk [![orcid_id][orcid_logo] 0000-0003-2576-4042](https://orcid.org/0000-0003-2576-4042)
- Marcin Górecki [![orcid_id][orcid_logo] 0000-0001-7472-3875](https://orcid.org/0000-0001-7472-3875)
