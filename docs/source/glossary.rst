Conventions and Terms
=====================

Reading and writing
-------------------

``tesliper`` was designed to deal with multiple conformers of a single molecule. It
identifies conformers using a stem of an extracted file (i.e. its filename without
extension). When files with identical names (save extension) are extracted in course of
subsequent :meth:`.Tesliper.extract` calls (or in recursive extraction, see method's
documentation), they are treated as the same conformer. This enables to join data
from subsequent calculations steps, e.g. geometry optimization, vibrational spectra
simulation, and electronic spectra simulation.

.. note::
    If specific data genre is available from more than one file, only recently
    extracted values will be stored.

Also, writing extracted and calculated data to files is done in batch, as usually
multiple files are produced. Hence, ``tesliper`` will chose names for these files
automatically, only allowing to specify output directory (as
:attr:`.Tesliper.output_dir` attribute). If you need more control over this process,
you will need to use one of the writer objects directly. These are easily available
*via* the :func:`.writer_base.writer` factory function.

Handling data
-------------

``tesliper`` stores multiple data entries of various types for each conformer. To
prevent confusion with Python's data ``type`` and with data itself, ``tesliper`` refers
to specific kinds of data as *genres*. Genres in code are represented by specific
strings, used as identifiers. To learn about data genres known to ``tesliper``, see
documentation for :class:`.GaussianParser`, which lists them.

.. note::
    Given the above, you may wonder why is it *genres* and not just *kinds* of data
    then? The reason is that naming things is hard (one of the only two hard things in
    Computer Science, as `Phil Karlton said
    <https://www.karlton.org/2017/12/naming-things-hard/>`_). As of time of deciding on
    this name, I did not come up with the second one. Hopefully, this small oddity will
    not bother you too much.

``tesliper`` may not work properly when used to process data concerning different
molecules (i.e. having different number of atoms, different number of degrees of
freedom, etc.). If you want to use it for such purpose anyway, you may set
:attr:`Tesliper.conformers.allow_data_inconsistency <
.Conformers.allow_data_inconsistency>` to ``True``. ``tesliper`` will then stop
complaining and try to do its best.

Glossary
--------

genre
    A specific kind of data, e.g. SCF energy, dipole strengths, atoms' positions in
    space, or command used for calculations. Represented in code by a short string. Not
    to be confused with Python's data ``type``. See :ref:`available genres`.

trimming
    Internally marking certain conformers as *not kept*. ``tesliper`` provides an easy
    way to trim conformers to user's needs, see :ref:`trimming conformers`.

kept
    Conformers may be internally marked as *kept* or *not kept*. *Kept* conformers
    will be normally processed by ``tesliper``, *not kept* conformers will be ignored.
    See :attr:`.Conformers.kept`.

arrayed
    About data turned into an instance of :class:`.DataArray`-like object, usually by
    :class:`.Conformers`' method of the same name. See :meth:`.Conformers.arrayed`.

data array
    Type of objects used by ``tesliper`` to handle data read from multiple conformers.
    The same data array class may be used to represent more than one genre. Sometimes
    referred to as :class:`.DataArray`-like classes or objects. See :mod:`.arrays`.

data inconsistency
    An event of data having non-uniform properties, e.g. when number of values doesn't
    match number of conformers, or when some conformers provide a different number of
    values than other conformers for a particular data genre. See :mod:`.array_base`.
