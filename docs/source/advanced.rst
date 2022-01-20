Advanced guide
==============

``tesliper`` handles data extracted from the source files in a form of specialized
objects, called :term:`data array`\s. These objects are instances of one of the
:class:`.DataArray` subclasses (hence sometimes referenced as ``DataArray``-like
objects), described here in a greater detail. :class:`.DataArray` base class defines a
basic interface and implements data validation, while its subclasses provided by
``tesliper`` define how certain data :term:`genre`\s should be treated and processed.

.. note::

    Under the hood, :term:`data array`\s, and ``tesliper`` in general, use `numpy
    <https://numpy.org>`_ to provide fast numeric operations on data.

This part of documentation also shows how to take more control over the data export.
:class:`.Tesliper` autotomizes this process quite a bit and exposes only a limited set
of possibilities provided by the underlying writer classes. It will be shown here how to
use these writer classes directly in your code.

Data array classes
------------------

Each ``DataArray``-like object has the following four attributes:

genre
    name of the data genre that *values* represent;
filenames
    sequence of conformers' identifiers as a ``numpy.ndarray(dtype=str)``;
values
    sequence of values of *genre* data genre for each conformer in *filenames*. It is
    also a :class:`numpy.ndarray`, but its ``dtype`` depends on the particular data
    array class;
allow_data_inconsistency
    a flag that controls the process of data validation. More about data inconsistency
    will be said later.

Some data arrays may provide more data. For example, any spectral data values wouldn't
be complete without the information about the band that they corresponds to, so data
arrays that handle this kind of data also provide a *frequencies* or *wavelengths*
attribute.

.. note::

    Attributes that hold a band information are actually *freq* and *wavelen*
    respectively, *frequencies* and *wavelengths* are convenience aliases.


Creating data arrays
''''''''''''''''''''

The easiest way to instantiate the data array of desired data genre is to use
:meth:`.Conformers.arrayed` factory method. It transforms it's stored data into the
``DataArray``-like object associated with a particular data genre, ignoring any
conformer that is :term:`not kept <kept>` or doesn't provide data for the requested
genre. You may force it to ignore any trimming applied by adding ``full=True`` to call
parameters (conformers without data for requested genre still will be ignored).
Moreover, any other keyword parameters provided will be forwarded to the class
constructor, allowing you to override any default values.

.. code-block:: python

    >>> from tesliper import Conformers
    >>> c = Conformers(
    ...     one={"gib":-123.5},
    ...     two={},
    ...     three={"gib": -123.6},
    ...     four={"gib":-123.7}
    ... )
    >>> c.kept = ["one", "three"]
    >>> c.arrayed("gib")
    Energies(genre='gib', filenames=['one' 'three'], values=[-123.5 -123.6], t=298.15)
    >>> c.arrayed("gib", full=True) 
    Energies(genre='gib', filenames=['one' 'three' 'four'], values=[-123.5 -123.6 -123.7], t=298.15)
    >>> c.arrayed("gib", t=1111)             
    Energies(genre='gib', filenames=['one' 'three'], values=[-123.5 -123.6], t=1111)

You can also instantiate any data array directly, providing data by yourself.

.. code-block:: python

    >>> from tesliper import Energies
    >>> Energies(
    ...     genre='gib', 
    ...     filenames=['one' 'three'], 
    ...     values=[-123.5 -123.6]
    ... )
    Energies(genre='gib', filenames=['one' 'three'], values=[-123.5 -123.6], t=298.15)


Data validation
'''''''''''''''

On instantiation of a data array class, *values* provided to its constructor are
transformed to the ``numpy.ndarray`` of the appropriate type. If this cannot be done
due to the incompatibility of type of *values* elements and data array's ``dtype``,
an exception is raised. However, ``tesliper`` will try to convert given values to the
target type, if possible.

.. code-block:: python

    >>> from tesliper import IntegerArray
    >>> arr = IntegerArray(genre="example", filenames=["one"], values=["1"])
    >>> arr
    IntegerArray(genre="example", filenames=["one"], values=[1])
    >>> type(arr.values)
    <class 'numpy.ndarray'>

    >>> IntegerArray(genre="example", filenames=["one"], values=["1.0"])
    Traceback (most recent call last):
    ...
    ValueError: invalid literal for int() with base 10: '1.0'

    >>> IntegerArray(genre="example", filenames=["one"], values=[None])
    Traceback (most recent call last):
    ...
    TypeError: int() argument must be a string, a bytes-like object or a number, not 'NoneType

Also *values* size is checked: its first dimension must be of the same size, as the
number of entries in the *filenames*, otherwise :exc:`ValueError` is raised.

.. code-block:: python

    >>> IntegerArray(genre="example", filenames=["one"], values=[1, 2])
    Traceback (most recent call last):
    ...
    ValueError: values and filenames must have the same shape up to 1 dimensions. Arrays of shape (2,) and (1,) were given.

:exc:`.InconsistentDataError` exception is raised when *values* are multidimensional,
but provide uneven number of entries for each conformer (*values* are a jagged array).

.. code-block:: python

    >>> IntegerArray(genre="example", filenames=["one", "two"], values=[[1, 2], [3]])
    Traceback (most recent call last):
    ...
    InconsistentDataError: IntegerArray of example genre with unequal number of values for conformer requested.

This behavior may be suppressed, if the instance is initiated with
``allow_data_inconsistency=True`` keyword parameter. In such case no exception is raised
if numbers of entries doesn't match, and jagged arrays will be turned into
``numpy.ma.masked_array`` instead of ``numpy.ndarray``, if it is possible.

.. code-block:: python

    >>> IntegerArray(
    ...     genre="example", 
    ...     filenames=["one"], 
    ...     values=[1, 2],
    ...     allow_data_inconsistency=True
    ... )
    IntegerArray(genre="genre", filenames=["one"], values=[1,2], allow_data_incosistency=True)

    >>> IntegerArray(
    ...     genre="example", 
    ...     filenames=["one", "two"], 
    ...     values=[[1, 2], [3]],
    ...     allow_data_inconsistency=True
    ... )
    IntegerArray(genre='genre', filenames=['one' 'two'], values=[[1 2]
     [3 --]], allow_data_inconsistency=True)

Some data array classes validate also other data provided to its constructor, e.g.
:class:`.Geometry` checks if *atoms* provides an atom specification for each atom in the
conformer.

.. note::
    Each validated field is actually a :class:`.ArrayProperty` or its subclass under the
    hood, which provides the validation mechanism.

Available data arrays
'''''''''''''''''''''

Data arrays provided by ``tesliper`` are listed below in categories, along with a short
description and with a list of data genres that are associated with a particular data
array class. More information about a ``DataArray``-like class of interest may be learn
in the :mod:`API reference <tesliper.glassware.arrays>`.


Generic types
"""""""""""""

Simple data arrays, that hold a data of particular type. They do not provide any
functionality beside initial data validation. They are used by ``tesliper`` for
segregation of simple data an as a base classes for other data arrays (concerns mostly
:class:`.FloatArray`).

:class:`.IntegerArray`
    For handling data of ``int`` type.

    .. list-table:: Genres associated with this class:
        :width: 100%

        * - charge
          - multiplicity

:class:`.FloatArray`
    For handling data of ``float`` type.

    .. list-table:: Genres associated with this class:
        :width: 100%

        * - zpecorr
          - tencorr
          - entcorr
          - gibcorr

:class:`.BooleanArray`
    For handling data of ``bool`` type.

    .. list-table:: Genres associated with this class:
        :width: 100%

        * - normal_termination
          - optimization_completed

:class:`.InfoArray`
    For handling data of ``str`` type.

    .. list-table:: Genres associated with this class:
        :width: 100%

        * - command
          - stoichiometry

Spectral data
"""""""""""""

Each data array in this category provides a *freq* or *wavelen* attribute, also
accessible by their convenience aliases *frequencies* and *wavelengths*. These
attributes store an information about frequency or wavelength that the particular
spectral value is associated with (x-axis value of the center of the band).

Activities genres, that are the genres that may be used to simulate the spectrum, also
provide a *calculate_spectra()* method for this purpose (see
:meth:`.VibrationalActivities.calculate_spectra`,
:meth:`.ScatteringActivities.calculate_spectra`, and
:meth:`.ElectronicActivities.calculate_spectra`), as well as a
:attr:`~.SpectralActivities.intensities` property that calculates a theoretical
intensity for each activity value. A convince :attr:`~.SpectralActivities.spectra_name`
property may be used to get the name of spectra pseudo-genre calculated with particular
activities genre.

.. code-block:: python

    >>> act = c["dip"]
    >>> act.spectra_name
    "ir"
    >>> from tesliper import lorentzan
    >>> spc = act.calculate_spectra(
    ...     start=200,  # cm^(-1)
    ...     stop=1800,  # cm^(-1)
    ...     step=1,     # cm^(-1)
    ...     width=5,    # cm^(-1)
    ...     fitting=lorentzan
    )
    >>> type(spc), spc.genre
    (<class 'tesliper.glassware.spectra.Spectra'>, 'ir')

:class:`.VibrationalData`
    For handling vibrational (IR and VCD related) data that is not a spectral activity.

    .. list-table:: Genres associated with this class:
        :width: 100%

        * - mass
          - frc
          - emang

:class:`.ScatteringData`
    For handling scattering (Raman and ROA related) data that is not a spectral activity.

    .. list-table:: Genres associated with this class:
        :width: 100%

        * - depolarp
          - depolaru
          - depp
          - depu
          - alpha2
        * - beta2
          - alphag
          - gamma2
          - delta2
          - cid1
        * - cid2
          - cid3
          - rc180
          -
          -

:class:`.ElectronicData`
    For handling electronic (UV and ECD related) data that is not a spectral activity.

    .. list-table:: Genres associated with this class:
        :width: 100%

        * - eemang

:class:`.VibrationalActivities`
    For handling vibrational (IR and VCD related) spectral activity data.

    .. list-table:: Genres associated with this class:
        :width: 100%

        * - iri
          - dip
          - rot

:class:`.ScatteringActivities`
    For handling scattering (Raman and ROA related) spectral activity data.

    .. list-table:: Genres associated with this class:
        :width: 100%

        * - ramanactiv
          - ramact
          - raman1
          - roa1
        * - raman2
          - roa2
          - raman3
          - roa3

:class:`.ElectronicActivities`
    For handling electronic (UV and ECD related) spectral activity data.

    .. list-table:: Genres associated with this class:
        :width: 100%

        * - vdip
          - ldip
          - vrot
          - lrot
          - vosc
          - losc

Other data arrays
"""""""""""""""""

:class:`.FilenamesArray`
    Special case of :class:`.DataArray`, holds only filenames. *values* property
    returns same as *filenames* and ignores any value given to its setter.
    The only genre associated with this class is *filenames* pseudo-genre.

:class:`.Bands`
    Special kind of data array for band values, to which spectral data or activities
    correspond. Provides an easy way to convert values between their different
    representations: frequency, wavelength, and excitation energy. Also allows to easily
    locate conformers with imaginary frequencies.

    .. code-block:: python

        >>> arr = Bands(
        ...     genre="freq",
        ...     filenames=["one", "two", "three"],
        ...     values=[[-15, -10, 105], [30, 123, 202], [-100, 12, 165]]
        ... )
        >>> arr.imaginary
        array([2, 0, 1])
        >>> arr.find_imaginary()
        {'one': 2, 'three': 1}

    .. list-table:: Genres associated with this class:
        :width: 100%

        * - freq
          - wavelen
          - ex_en

:class:`.Energies`
    For handling data about the energy of conformers. Provides an easy way of
    calculating Boltzmann distribution-based population of conformers *via* a
    :attr:`~.Energies.populations` property.

    .. code-block:: python

        >>> arr = Energies(
        ...     genre="gib", 
        ...     filenames=["one", "two", "three"], 
        ...     values=[-123.505977, -123.505424, -123.506271]
        ... )
        >>> arr.deltas  # difference from lowest energy in kcal/mol
        array([0.18448779, 0.53150055, 0.        ])
        >>> arr.populations
        array([0.34222796, 0.19052561, 0.46724643])

    .. list-table:: Genres associated with this class:
        :width: 100%

        * - scf
          - zpe
          - ten
          - ent
          - gib

:class:`.Transitions`
    For handling information about electronic transitions from ground
    to excited state contributing to each band.

    Data is stored in three attributes: :attr:`~.Transitions.ground`,
    :attr:`~.Transitions.excited`, and :attr:`~.Transitions.values`, which are
    respectively: list of ground state electronic subshells, list of excited state
    electronic subshells, and list of coefficients of transitions from corresponding
    ground to excited subshell. Each of these arrays is of shape (conformers, bands,
    max_transitions), where 'max_transitions' is a highest number of transitions
    contributing to single band across all bands of all conformers.

    Allows to easily calculate contribution of each transition using
    :attr:`~.Transitions.contribution` and to find which transition contributes the most
    to the particular transition with :attr:`~.Transitions.highest_contribution`. 

    .. list-table:: Genres associated with this class:
        :width: 100%

        * - transitions

:class:`.Geometry`
    For handling information about geometry of conformers.

    .. list-table:: Genres associated with this class:
        :width: 100%

        * - last_read_geom
          - input_geom
          - optimized_geom

Writing to disk
---------------

:class:`.Tesliper` object provides an easy, but not necessarily a flexible way of
writing calculated and extracted data to disk. If your process requires more flexibility
in this matter, you may use ``teslier``\s writer objects directly. This will allow you
to adjust how generated files are named and will give you more control over what is
exported.

A writer object may be created using a :func:`.writer` factory function. It expects a
string parameter, that specifies a desired format for data export. ``tesliper`` provides
writers for ``"txt"``, ``"csv"``, ``"xlsx"``, and ``"gjf"`` file formats. The second
mandatory parameter is a *destination*: the (existing) directory to which files should
be written. Just like writing methods of :class:`.Tesliper` object, the function also
takes a *mode* parameter that defines what should happen if any file already exists. Any
additional keyword parameters are forwarded to the writer object constructor.

.. code-block:: python

    >>> from tesliper import writer
    >>> wrt = writer("txt", "/path/to/dir")
    >>> type(wrt)
    <class 'tesliper.writing.txt_writer.TxtWriter'>

    >>> wrt = writer("txt", "/doesnt/exists")
    Traceback (most recent call last):
    ...
    FileNotFoundError: Given destination doesn't exist or is not a directory.

.. note::

    You can also create any of the writer objects directly, by importing and
    instantiating its class.
    
    .. code-block:: python

        from tesiper import TxtWriter
        wrt = TxtWriter(destination="/path/to/dir")

    :func:`.writer` factory function is used by ``tesliper`` mostly to provide a dynamic
    access to the writer class most recently registered (implemented) to handle a
    particular format. This is useful when you modify an existing writer class or
    provide a new one.

Writer objects expect data they receive to be a :class:`.DataArray`-like instances. Each
writer object provides a :meth:`~.WriterBase.write` method for writing arbitrary data
arrays to disk. This method dispatches received data arrays to appropriate writing
methods, based on their type. The table below lists these methods, along with a brief
description and :class:`.DataArray`-like object, for which the method will be called by
writer's :meth:`~.WriterBase.write` method.

.. list-table:: Methods used by default to write certain data
    :header-rows: 1

    * - Writer's Method
      - Description
      - Associated array
    * - :meth:`~.WriterBase.generic`
      - Generic data: any genre that provides one value for each conformer.
      - :class:`.DataArray`, :class:`.IntegerArray`,
        :class:`.FloatArray`, :class:`.BooleanArray`, :class:`.InfoArray`.
    * - :meth:`~.WriterBase.overview`
      - General information about conformers: energies, imaginary frequencies,
        stoichiometry.
      - :class:`.Energies`
    * - :meth:`~.WriterBase.energies`
      - Detailed information about conformers' relative energy,
        including calculated populations
      - :class:`.Energies`
    * - :meth:`~.WriterBase.single_spectrum`
      - A spectrum - calculated for single conformer or averaged.
      - :class:`.SingleSpectrum`
    * - :meth:`~.WriterBase.spectral_data`
      - Data related to spectral activity, but not convertible to spectra.
      - :class:`.SpectralData`
    * - :meth:`~.WriterBase.spectral_activities`
      - Data that may be used to simulate conformers' spectra.
      - :class:`.SpectralActivities`
    * - :meth:`~.WriterBase.spectra`
      - Spectra for multiple conformers.
      - :class:`.Spectra`
    * - :meth:`~.WriterBase.transitions`
      - Electronic transitions from ground to excited state, contributing to each band.
      - :class:`.Transitions`
    * - :meth:`~.WriterBase.geometry`
      - Geometry (positions of atoms in space) of conformers.
      - :class:`.Geometry`

Not all writer objects implement each of these writing methods, e.g.
:class:`.GjfWriter`, that allows to create Gaussian input files, only implements
:meth:`~.GjfWriter.geometry` method (because export of, e.g. a calculated spectrum as a
Gaussian input would be pointless). Trying to ``write()`` a data array that should be
written by a method that is not implemented, or calling such method directly, will raise
a :exc:`NotImplementedError`.

.. warning::

    You need to make sure that data contained in ``DataArray``-like objects cover the
    same set of conformers, when passing multiple data array objects to the
    :meth:`~.WriterBase.write` method or any other writing method. Passing two data
    arrays with data for different sets of conformers may produce files with corrupted
    data or fail silently. :meth:`.Conformers.trim_incomplete` trimming method may be
    helpful in preventing such fails.

Naming files
''''''''''''

Usually, calling any of writing methods will produce multiple files in the *destination*
directory: one for each given genre, each conformer, etc. ``tesliper`` provides a
reasonable naming scheme for these files, but you can modify it, by providing your own
*name_template*\s in place of the default ones. To do this you will need to call
desired writing methods directly, instead of using :meth:`~.WriterBase.write`.

Each writing method uses a value of *name_template* parameter given to the method call
to create a filename for each file it generates. *name_template* should be a string that
contains (zero, one, or more) label identifiers in form of ``${identifier}``. These
identifiers will be substituted to produce a final filename. Available identifiers and
their meaning are as follows:

| ``${ext}`` - appropriate file extension;
| ``${conf}`` - name of the conformer;
| ``${num}`` - number of the file according to internal counter;
| ``${genre}`` - genre of exported data;
| ``${cat}`` - category of produced output;
| ``${det}`` - category-specific detail.

The ``${ext}`` identifier is filled with the value of Writers ``.extension`` attribute,
which value is also used to identify a writer class: ``"txt"``, ``"csv"``, etc. Other
values are provided by the particular writing method.

.. code-block:: python

    from tesiper import Tesliper, writer
    tslr = Tesliper(input_dir="/project/input")
    ...  # data extracted and trimmed
    # tslr.conformers.kept_keys() == {"conf_one", "conf_four"}
    freq, dip, rot = tslr["freq"], tslr["dip"], tslr["rot"]
    wrt = writer("txt", "/project/default")
    wrt.spectral_activities(band=freq, data=[dip, rot])
    wrt = writer("txt", "/project/custom")
    wrt.spectral_activities(
        band=freq, data=[dip, rot],
        name_template="name_${num}_${genre}.xy"
    )

.. code-block:: none
    :caption: contents of ``/project``

    .
    ├───input
    │   └─── ...
    ├───default
    │   ├───conf_one.activities-vibrational.txt
    │   └───conf_four.activities-vibrational.txt
    └───custom
        ├───name_1_freq.xy
        └───name_2_freq.xy

