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
    sequence of conformers' identifiers as a ``numpy.ndarray(tdype=str)``;
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

Data arrays provided by ``tesliper`` are listed below in categories, along with a short
description and with a list of data genres that are associated with a particular data
array class. More information about a ``DataArray``-like class of interest may be learn
in the :mod:`API reference <tesliper.glassware.arrays>`


Generic types
'''''''''''''

Simple data arrays, that hold an information of particular data type. They do not
provide any functionality beside initial data validation.

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
'''''''''''''

Each data array in this category provides a *freq* or *wavelen* attribute, also
accessible by their convenience aliases *frequencies* and *wavelengths*. These
attributes store an information about frequency or wavelength that the particular
spectral value is associated with (x-axis value of the center of the band).
Activities genres, that are the genres that may be used to simulate the spectrum,
also provide a *calculate_spectra()* method for this purpose.

:class:`.VibrationalData`
    For handling vibrational data that is not a spectral activity.

    .. list-table:: Genres associated with this class:
        :width: 100%

        * - mass
          - frc
          - emang

:class:`.ScatteringData`
    For handling scattering data that is not a spectral activity.

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
    For handling electronic data that is not a spectral activity.

    .. list-table:: Genres associated with this class:
        :width: 100%

        * - eemang

:class:`.VibrationalActivities`
    For handling electronic spectral activity data.

    .. list-table:: Genres associated with this class:
        :width: 100%

        * - iri
          - dip
          - rot

:class:`.ScatteringActivities`
    For handling scattering spectral activity data.

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
    For handling electronic spectral activity data.

    .. list-table:: Genres associated with this class:
        :width: 100%

        * - vdip
          - ldip
          - vrot
          - lrot
          - vosc
          - losc

Other data arrays
'''''''''''''''''

:class:`.FilenamesArray`
    Special case of :class:`.DataArray`, holds only filenames. *values* property
    returns same as *filenames* and ignores any value given to its setter.
    The only genre associated with this class is *filenames* pseudo-genre.

:class:`.Bands`
    Special kind of data array for band values, to which spectral data or activities
    correspond. Provides an easy way to convert values between their different
    representations: frequency, wavelength, and excitation energy.

    .. list-table:: Genres associated with this class:
        :width: 100%

        * - freq
          - wavelen
          - ex_en

:class:`.Energies`
    For handling data about the energy of conformers. Provides an easy way of
    calculating Boltzmann distribution-based population of conformers *via* a
    :attr:`~.Energies.populations` property.

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

