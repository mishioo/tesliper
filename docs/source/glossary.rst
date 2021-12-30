Conventions and Terms
=====================

There are some conventions that are important to note:

 
``tesliper`` stores multiple data entries of various types for each conformer. To
prevent confusion with Python's data ``type`` and with data itself, ``tesliper`` refers
to specific kinds of data as "genres". Genres in code are represented by specific
strings, used as identifiers. To learn about data genres known to ``tesliper``, see
documentation for :class:`.GaussianParser`, which lists them.

``tesliper`` identifies conformers using stem of an extracted file (i.e. its filename
without extension). When files with identical names are extracted in course of
subsequent :meth:`.Tesliper.extract` calls or in recursive extraction using
``tesliper_object.extract(recursive=True)``, they are treated as data for one conformer.
This enables to join data from subsequent calculations steps, e.g. geometry
optimization, vibrational spectra simulation, and electronic spectra simulation. Please
note that if specific data genre is available from more than one calculation job, only
recently extracted values will be stored.

``tesliper`` was designed to deal with multiple conformers of single molecule and may
not work properly when used to process data concerning different molecules (i.e. having
different number of atoms, different number of degrees of freedom, etc.). If you want to
use it for such purpose anyway, you may set
:attr:`Tesliper.conformers.allow_data_inconsistency <
.Conformers.allow_data_inconsistency>` to ``True``. ``tesliper`` will then stop
complaining and try to do its best.

Glossary
--------

genre
    A specific kind of data, e.g. SCF energy, dipole strengths, atoms' positions in
    space, or command used for calculations. Represented in code by a short string. Not
    to be confused with Python's data ``type``.

trimming
    Internally marking certain conformers as *not kept*. ``tesliper`` provides an easy
    way to trim conformers to user's needs, see :ref:`trimming conformers`.

kept
    Conformers may be internally marked as *kept* or *not kept*. *Kept* conformers
    will be normally processed by ``tesliper``, *not kept* conformers will be ignored.
    See 

arrayed

data array
    Type of objects used by ``tesliper`` to handle data read from multiple conformers.
    The same data array class may be used to represent more than one genre. Sometimes
    referred to as :class:`.DataArray`-like classes or objects. See :mod:`.arrays`
    for more information.

data inconsistency
