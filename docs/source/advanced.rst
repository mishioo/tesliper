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


Generic types
'''''''''''''

.. autoclass:: tesliper.glassware.arrays.IntegerArray
    :class-doc-from: class

.. autoclass:: tesliper.glassware.arrays.FloatArray
    :class-doc-from: class

.. autoclass:: tesliper.glassware.arrays.BooleanArray
    :class-doc-from: class

.. autoclass:: tesliper.glassware.arrays.InfoArray
    :class-doc-from: class

