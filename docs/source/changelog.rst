Change Log
==========

v. 0.9.2
--------

Bug Fixes:
    - Fixed ``__version__`` and other metadata attributes broken in 0.9.1.

v. 0.9.1
--------

Bug Fixes:
    - Fixed ``ImportError`` occurring in Python 3.10.
    - Corrected creation of ``"filanemes"`` pseudo-genre.
    - Corrected ``len()`` behavior with ``Spectra`` instances.

New Features:
    - Added "top-level" temperature setting in both, API and GUI.
    - Allowed ignoring of unexpected keyword arguments in ``Conformers.arrayed()``.

Other Changes:
    - Moved requirements to setup.py file.
    - Added ``tesliper-gui`` entry point.
    - ``Tesliper.get_averaged_spectrum()`` now tries to calculate missing spectra.
    - Minor supplementation to documentation and READEME.

v. 0.9.0
--------

Created online documentation! Available at https://tesliper.readthedocs.io/

Bug Fixes:
    - Fixed error on parsing radical molecules.
    - Corrected ``ArrayProperty`` ignoring it's ``.fill_value``.
    - Fixed infinite recursion error on ``SpectralData.wavelen`` access.
    - Prevented creation of empty files on export of empty data arrays.
    - Prevented intermediate ``.xlsx`` file saving when exporting multiple data genres.
    - Corrected trimming abnormally terminated conformers in GUI.

New Features:
    - ``rmsd_sieve`` and ``Conformers.trim_rmsd`` now allow for arbitrary windows.
    - Added ``datawork.geometry.pyramid_windows`` window strategy function.
    - Extended ``Soxhlet`` to allow use of arbitrary registered parsers.
    - Allowed for automatic instantiation of data arrays for genres that depend on a different genre.
    - Introduced *optimized_geom* genre
    - Added export of generic data arrays.
    - Added parametrization of ``GjfWriter.link0`` commands.

Other Changes:
    - Reviewed and corrected calculation of intensities.
    - Improved automatic scaling of spectra.
    - Renamed ``Parser`` to ``ParserBase`` for consistency with other base classes.
    - Unified base classes' registering mechanism of their subclasses.
    - Cleaned up ``extraction.gaussian_parser``. Changed all data sequences to lists. 
    - Supplemented type hints.
    - Renamed *geometry* genre to *last_read_geom*.
    - Supplemented ``Conformers`` to fully implement ``OrderedDict`` interface.
    - Added storage and serialization of experimental spectra.

GUI:
    - Unified terminology used with the one in code and documentation.

v. 0.8.2
--------

API:
    - Corrected data export when ``Tesliper``'s default genres used.
    - Corrected error when ``Tesliper.calculate_spectra`` called with default values.
    - Corrected default filenames generated for spectral data and activities.
    - Supplemented genres' full names and other metadata.

v. 0.8.1
--------

API:
    - Corrected handling of invalid start, stop, step parameters combination when calculating spectra.
GUI:
    - Fixed incorrect floats' rounding in numeric entries.
    - Added reaction (trim conformers/redraw spectra) to "Enter" key press, when editing a numeric entry.
    - Fixed an error occurring when "show activities" is checked but there are no activities in a plotting range.
    - Added auto-update of energies-related values after trimming.


v. 0.8.0
--------

API:
    - added RMSD-based trimming of conformers with similar geometry
    - added auto scaling and shifting spectra to match reference
    - added support for handling and exporting electronic transitions
    - added export to .gjf files
    - added serialization of ``Tesliper`` class
    - renamed ``Molecules`` class to ``Conformers``
    - significant changes to ``...Writer`` classes
    - significant changes to ``DataArray`` subclasses
    - major code refactoring
    - many smaller changes and improvements
GUI:
    - new application layout
    - added scroll response to numeric fields
    - changed available and default colour schemes
    - supplemented data export options


v. 0.7.4
--------

API:
    - Tesliper's method 'average_spectra' returns reference to dict of averaged spectra
GUI:
    - fixed files export (broken in v. 0.7.3)


v. 0.7.3
--------

API:
    - introduced exceptions.py submodule
    - glassware module turned into package
    - improved mechanism for dealing with inconsistent data sizes
    - added mechanism for trimming conformers with inconsistent data sizes
    - fixed Molecules' trim_incomplete function
    - enhanced Molecules' trim_non_matching_stoichiometry function
    - introduced dict_view classes for iteration through trimmed Molecules 
    - improved Molecules indexing mechanism to return in O(1)
    - removed 'cpu_time' from data extracted by gaussian_parser
    - fixed error on parsing ECD calculations from g.09B 
GUI:
    - fixed problem with stacked spectra drawing 
    - added spectra reversing on demand
    - fixed stacked spectra coloring
    - corrected bars drawing for uv and ecd spectra
    - added option for filtering conformers with inconsistent data sizes
    - split un/check into separate buttons
    - fixed checking/unchecking incomplete entries
    - added checking/unchecking inconsistent sizes
    - other minor changes and fixes


v. 0.7.2
--------

- added support for string 'genres' parameter in Tesliper.calculate_spectra method
- added support for .xy spectra files
- gui: fixed problem with averaged and stacked spectra drawing 
- gui: set "user_home_dir/tesliper/" as default location for tslr_err_log.exe
- other minor fixes and enhancements


v. 0.7.1
--------

- fixed crash on spectra drawing when Matplotlib 3 used
- fixed problem with loading spectra from some txt files
- added support for loading spectra from csv files
- other minor fixes


v. 0.7.0
--------

- graphical user interface redesigned
- significant changes in code architecture
- many fixes


v. 0.6.4
--------

- calculated spectra precision in txt files changed to e-4
- spectra lines width changed
- data trimming features corrected
- spectra plot erasing on session clearing implemented
- inverting x axis for uv and ecd spectra added


v. 0.6.3
--------

- fixed export error when not chosen, but all data were exported
- fixed export error when export occurred after closing popup window
- fixed export error when energies were not exported to separate txt files
- entry validation improved


v. 0.6.2
--------

- solved some problems with corrupted files extraction
- added warning when files from mixed gaussian runs found
- fixed RuntimeError on overlapping actions
- fixed export popup error
- errors description moved to tslr_err_log.txt
- fixed ValueError on empty settings in gui_main.current_settings
- corrected session instantiation from files (unwanted files problem)
- changed energies precision to .6
- added Min. Boltzmann factor in GUI


v. 0.6.1
--------

First beta release


v. 0.6.0 and earlier
--------------------

Early development stages