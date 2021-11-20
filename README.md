[![Build status](https://ci.appveyor.com/api/projects/status/vh0t6udj7mnpnfoe?svg=true)](https://ci.appveyor.com/project/mishioo/tesliper-jjshl)
[![Coverage Status](https://coveralls.io/repos/github/mishioo/tesliper/badge.svg)](https://coveralls.io/github/mishioo/tesliper)
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
  - [Using in Python scripts](#using-in-python-scripts)
    - [Basics](#basics)
    - [Filtering conformers](#filtering-conformers)
    - [Available data genres](#available-data-genres)
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
[latest relase](https://github.com/Mishioo/tesliper/releases/tag/0.8.0).
This file is a standalone application, no installation is required.

# Documentation

Full documentation is on its way! For now please refer to the short tutorial below.

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
known to `tesliper`, see [Available data genres](#available-data-genres) section,
which lists them.
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
### Basics
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
>>> tslr.wanted_files = ["one", "two", "three"]  # only files with this names
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

When modifying `Tesliper.parameters` be cerfull to not delete any of the parameters.
If you need to revert to standard parameters values, you can find them in
`Tesliper.standard_parameters`.
```
>>> tslr.parameters["ir"] = {
...     "start": 500, "stop": 2500, "width": 2
... }  # this will cause problems!
>>> tslr.parameters = tslr.standard_parameters  # revert to default values
```

Trimming functionality, used in previous example in
`tslr.conformers.trim_not_optimized()`, allows you to filter out conformers that
shouldn't be used in further processing and analysis. You can trim off conformers
that were not optimized, contain imaginary frequencies, or have other unwanted
qualities. Conformers with similar geometry may be discarded using an RMSD sieve.
For more information about trimming, please refer to
[Filtering conformers](#filtering-conformers) section.

For more exploratory analysis, `Tesliper` provides an easy way to access desired
data as an instance of specialized `DataArray` class. Those objects implement
a number of convenience methods for dealing with specific data genres.
To get data in this form use `array = tslr["genre"]` were `"genre"` is string with
the name of desired data genre. You may find a list of available genres in the section
[Available data genres](#available-data-genres).
```
>>> energies = tslr["gib"]
>>> energies.values
array([-304.17061762, -304.17232455, -304.17186735])
>>> energies.populations
array([0.0921304 , 0.56174031, 0.3461293 ])
>>> energies.full_name
'Thermal Free Energy'
```

Please note, that if some conformers do not provide values for a specific data
genre, it will be ignored when retriving data for `DataArray` instantiation,
regardles if it were trimmed off or not.
```
>>> tslr = Tesliper()
>>> tslr.conformers.update([
>>> ...     ('one', {'gib': -304.17061762}),
>>> ...     ('two', {'gib': -304.17232455}),
>>> ...     ('three', {'gib': -304.17186735}),
>>> ...     ('four', {})
>>> ... ])
>>> tslr.conformers.kept
[True, True, True, True]
>>> energies = tslr["gib"]
>>> energies.filenames
array(['one', 'two', 'three'], dtype='<U5')
```

### Filtering conformers
`tesliper` offers means to easily and quickly filter conformers with unwanted properties.
It calls such process a 'trimming'. A number of trimming methods are available via
`Tesliper.conformers` attribute, that stores data extracted so far. A brief reference
for these methods may be find below.

- `trim_imaginary_frequencies()`:
  mark all conformers with imaginary frequencies as "not kept".
- `trim_not_optimized()`:
  mark all conformers that failed structure optimization as "not kept".
- `trim_non_normal_termination()`:
  mark all conformers, which calculation job did not terminate normally, as "not kept".
- `trim_inconsistent_sizes()`:
  mark as "not kept" all conformers that contain any iterable data genre,
  that is of different length, than in case of majority of conformers.
- `trim_incomplete()`:
  mark incomplete conformers as "not kept".
- `trim_non_matching_stoichiometry(wanted: str)`:
  mark all conformers with stoichiometry other than `wanted` as "not kept".
  If not given, `wanted` evaluates to the most common stoichiometry.
- `trim_to_range(genre: str, minimum: float, maximum: float, attribute: str)`:
  marks as "not kept" all conformers, which numeric value of data
  of specified genre is outside of the range specified by `minimum`
  and `maximum` values. `attribute` is optional, it lets you specify if something
  other than original values should be considered (e.g. "populations" for energies 
  genre).
- `trim_rmsd(threshold: float, window_size: float, geometry_genre: str, energy_genre: str, ignore_hydrogen: bool)`:
  marks as "not kept" all conformers, that are not identical, according
  to provided RMSD threshold and energy difference. Conformers, which energy
  difference (dE) is higher than given `window_size` are always treated as
  different, while those with dE smaller than `window_size` and RMSD value
  smaller than given `threshold` are considered identical. From two identical
  conformers, the one with lower energy is "kept", and the other is discarded
  (marked as "not kept"). Used geometry genre and energies genre might be specified,
  otherwise default values of "geometry" and "scf" are assumed. `ignore_hydrogen`
  specifies if hydrogen atoms should be ignored when calculating RMSD values,
  it defaults to `True`.

You may also use `Tesliper.comformers.kept` to manipulate which conformers are
processed ("kept"), and which are not. This is a list of booleans, that may be
modified in a few ways, as described below.

Firstly, it is the
most straightforward to just assign a new list of boolean values to
the `kept` attribute. This list should have the same number of elements
as the number of conformers contained. A ValueError is raised if it
doesn't.
```
>>> c = tslr.conformers  # {one={}, two={}, tree={}}
>>> c.kept
[True, True, True]
>>> c.kept = [False, True, False]
>>> c.kept
[False, True, False]
>>> c.kept = [False, True, False, True]
Traceback (most recent call last):
...
ValueError: Must provide boolean value for each known conformer.
4 values provided, 3 excepted.
```
Secondly, list of filenames of conformers intended to be kept may be
given. Only these conformers will be kept. If given filename is not in
the underlying Conformers' dictionary, KeyError is raised.
```
>>> c.kept = ['one']
>>> c.kept
[True, False, False]
>>>  c.kept = ['two', 'other']
Traceback (most recent call last):
...
KeyError: Unknown conformers: other.
```
Thirdly, list of integers representing conformers indices may br given.
Only conformers with specified indices will be kept. If one of given integers
cant be translated to conformer's index, IndexError is raised. Indexing with
negative values is not supported currently.
```
>>> c.kept = [1, 2]
>>> c.kept
[False, True, True]
>>> c.kept = [2, 3]
Traceback (most recent call last):
...
IndexError: Indexes out of bounds: 3.
```
Fourthly, assigning `True` or `False` to this attribute will mark all conformers
as kept or not kept respectively.
```
>>> c.kept = False
>>> c.kept
[False, False, False]
>>> c.kept = True
>>> c.kept
[True, True, True]
```
Lastly, list of kept values may be modified by setting its elements
to True or False. It is advised against, however, as mistake such as
`m.kept[:2] = [True, False, False]` will break some functionality by
forcibly changing size of `kept` list.

### Available data genres
Data genres, their availability from specific types of calculation,
and their brief description are as follows:

- `freq`: list of floats, available from freq job --
    harmonic vibrational frequencies (cm^-1)
- `mass`: list of floats, available from freq job --
    reduced masses (AMU)
- `frc`: list of floats, available from freq job --
    force constants (mDyne/A)
- `iri`: list of floats, available from freq job --
    IR intensities (KM/mole)
- `dip`: list of floats, available from freq=VCD job --
    dipole strengths (10**-40 esu**2-cm**2)
- `rot`: list of floats, available from freq=VCD job --
    rotational strengths (10**-44 esu**2-cm**2)
- `emang`: list of floats, available from freq=VCD job --
    E-M angle = Angle between electric and magnetic dipole transition moments (deg)
- `depolarp`: list of floats, available from freq=Raman job --
    depolarization ratios for plane incident light
- `depolaru`: list of floats, available from freq=Raman job --
    depolarization ratios for unpolarized incident light
- `ramanactiv`: list of floats, available from freq=Raman job --
    Raman scattering activities (A**4/AMU)
- `ramact`: list of floats, available from freq=ROA job --
    Raman scattering activities (A**4/AMU)
- `depp`: list of floats, available from freq=ROA job --
    depolarization ratios for plane incident light
- `depu`: list of floats, available from freq=ROA job --
    depolarization ratios for unpolarized incident light
- `alpha2`: list of floats, available from freq=ROA job --
    Raman invariants Alpha2 = alpha**2 (A**4/AMU)
- `beta2`: list of floats, available from freq=ROA job --
    Raman invariants Beta2 = beta(alpha)**2 (A**4/AMU)
- `alphag`: list of floats, available from freq=ROA job --
    ROA invariants AlphaG = alphaG'(10**4 A**5/AMU)
- `gamma2`: list of floats, available from freq=ROA job --
    ROA invariants Gamma2 = beta(G')**2 (10**4 A**5/AMU)
- `delta2`: list of floats, available from freq=ROA job --
    ROA invariants Delta2 = beta(A)**2, (10**4 A**5/AMU)
- `raman1`: list of floats, available from freq=ROA job --
    Far-From-Resonance Raman intensities =ICPu/SCPu(180) (K)
- `roa1`: list of floats, available from freq=ROA job --
    ROA intensities =ICPu/SCPu(180) (10**4 K)
- `cid1`: list of floats, available from freq=ROA job --
    CID=(ROA/Raman)*10**4 =ICPu/SCPu(180)
- `raman2`: list of floats, available from freq=ROA job --
    Far-From-Resonance Raman intensities =ICPd/SCPd(90) (K)
- `roa2`: list of floats, available from freq=ROA job --
    ROA intensities =ICPd/SCPd(90) (10**4 K)
- `cid2`: list of floats, available from freq=ROA job --
    CID=(ROA/Raman)*10**4 =ICPd/SCPd(90)
- `raman3`: list of floats, available from freq=ROA job --
    Far-From-Resonance Raman intensities =DCPI(180) (K)
- `roa3`: list of floats, available from freq=ROA job --
    ROA intensities =DCPI(180) (10**4 K)
- `cid3`: list of floats, available from freq=ROA job --
    CID=(ROA/Raman)*10**4 =DCPI(180)
- `rc180`: list of floats, available from freq=ROA job --
    RC180 = degree of circularity
- `wavelen`: list of floats, available from td job --
    excitation energies (nm)
- `ex_en`: list of floats, available from td job --
    excitation energies (eV)
- `eemang`: list of floats, available from td job --
    E-M angle = Angle between electric and magnetic dipole transition moments (deg)
- `vdip`: list of floats, available from td job --
    dipole strengths (velocity)
- `ldip`: list of floats, available from td job --
    dipole strengths (length)
- `vrot`: list of floats, available from td job --
    rotatory strengths (velocity) in cgs (10**-40 erg-esu-cm/Gauss)
- `lrot`: list of floats, available from td job --
    rotatory strengths (length) in cgs (10**-40 erg-esu-cm/Gauss)
- `vosc`: list of floats, available from td job --
    oscillator strengths
- `losc`: list of floats, available from td job --
    oscillator strengths
- `transitions`: list of tuples of tuples of (int, int, float), available from td job --
    transitions (first to second) and their coefficients (third)
- `scf`: float, always available --
    SCF energy
- `zpe`: float, available from freq job --
    Sum of electronic and zero-point Energies (Hartree/Particle)
- `ten`: float, available from freq job --
    Sum of electronic and thermal Energies (Hartree/Particle)
- `ent`: float, available from freq job --
    Sum of electronic and thermal Enthalpies (Hartree/Particle)
- `gib`: float, available from freq job --
    Sum of electronic and thermal Free Energies (Hartree/Particle)
- `zpecorr`: float, available from freq job --
    Zero-point correction (Hartree/Particle)
- `tencorr`: float, available from freq job --
    Thermal correction to Energy (Hartree/Particle)
- `entcorr`: float, available from freq job --
    Thermal correction to Enthalpy (Hartree/Particle)
- `gibcorr`: float, available from freq job --
    Thermal correction to Gibbs Free Energy (Hartree/Particle)
- `command`: str, always available --
    command used for calculations
- `normal_termination`: bool, always available --
    true if Gaussian job seem to exit normally, false otherwise
- `optimization_completed`: bool, available from opt job --
    true if structure optimization was performed successfully
- `version`: str, always available --
    version of Gaussian software used
- `charge`: int, always available --
    molecule's charge
- `multiplicity`: int, always available --
    molecule's spin multiplicity
- `input_atoms`: list of str, always available --
    input atoms as a list of atoms' symbols
- `input_geom`: list of tuples of floats, always available --
    input geometry as X, Y, Z coordinates of atoms
- `stoichiometry`: str, always available --
    molecule's stoichiometry
- `molecule_atoms`: list of ints, always available --
    molecule's atoms as atomic numbers
- `geometry`: list of tuples of floats, always available --
    molecule's geometry (last one found in file) as X, Y, Z coordinates of atoms

`tesliper` also uses `ir`, `vcd`, `uv`, `ecd`, `raman`, and `roa` when referring
to calculated spectra.

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
