Scripting with ``tesliper``
===========================

This part discusses basics of using Python API. For tutorial on using a Graphical
Interface, see :ref:`gui`.

``tesliper`` provides a :class:`.Tesliper` class as a main entry point to its
functionality. This class allows you to easily perform any typical task: read and write
files, filter data, calculate and average spectra. It is recommended to read
:ref:`conventions` to get a general idea of what to expect. The next paragraphs will
introduce you to basic use cases with examples and explanations. The examples do not use
real data, but simplified mockups, to not obscure the logic presented.

.. code-block:: python

    from tesliper import Tesliper

    # extract data from Gaussian output files
    tslr = Tesliper(input_dir="./opt_and_freq")
    tslr.extract()

    # conditional filtering of conformers
    tslr.conformers.trim_non_normal_termination()
    tslr.conformers.trim_not_optimized()
    tslr.conformers.trim_imaginary_frequencies()
    tslr.conformers.trim_to_range("gib", maximum=10, attribute="deltas")
    tslr.conformers.trim_rmsd(threshold=1.0, window_size=0.5, energy_genre="gib")

    # calculate and average spectra, export data
    tslr.calculate_spectra()
    tslr.average_spectra()
    tslr.export_energies(fmt="txt")
    tslr.export_averaged(fmt="csv")

Reading files
-------------

After importing :class:`.Tesliper` class, we instantiate it with an *input_dir*
parameter, which is a path to the directory containing output files from quantum
chemical calculations software. You may also provide an *output_dir* parameter, defining
where ``tesliper`` should write the files it generates. Both of those parameters are
optional and default to the current working directory, if omitted. You may also provide
a *wanted_files* parameter, which should be a list of filenames that :class:`.Tesliper`
should parse, ignoring any other files present in *input_dir*. Omitting *wanted_files*
means that no file should be ignored.

.. note::
    
    :class:`.Tesliper` accepts also *quantum_software* parameter, which is a hint for
    ``tesliper`` on how it should parse output files it reads. However, only Gaussian
    software is supported out-of-the-box, and ``quantum_software="gaussian"`` is a
    default value. If you wish to use ``tesliper`` to work with another qc package,
    learn how to extend its functionality in the :ref:`extend` section.

You can extract data from the files in *output_dir* using :meth:`.Tesliper.extract`
method. :meth:`.Tesliper.extract` respects *input_dir* and *wanted_files* given to
:class:`.Tesliper`, but *path* and *wanted_files* parameters provided to the method call
will take precedence. If you would like to read files in the whole directory tree, you
may perform a recursive extraction, using ``extract(recursive=True)``. So assuming a
following directory structure::

    project
    ├── optimization
    │   ├── conf_one.out
    │   └── conf_two.out
    │   └── conf_three.out
    └── vibrational
        ├── conf_one.out
        └── conf_two.out
        └── conf_three.out

you could use any of the following to get the same effect.

.. code-block:: python

    # option 1: change *input_dir*
    tslr = Tesliper(input_dir="./project/optimization")
    tslr.extract()
    tslr.input_dir = "./project/vibrational"
    tslr.extract()

    # option 2: override *input_dir* only for one call
    tslr = Tesliper(input_dir="./project/optimization")
    tslr.extract()
    tslr.extract(path="./project/vibrational")

    # option 3: read the whole tree
    tslr = Tesliper(input_dir="./project")
    tslr.extract(recursive=True)


``tesliper`` will try to guess the extension of files it should parse: e.g. Gaussian
output files may have ".out" or ".log" extension. If those are mixed in the source
directory, an exception will be raised. You can prevent this by providing the
*extension* parameter, only files with given extension will be parsed.

.. code-block:: none

    project
    ├── conf_one.out
    └── conf_two.log
    
.. code-block:: python

    tslr = Tesliper(input_dir="./project")
    tslr.extract()  # raises ValueError
    tslr.extract(extension="out")  # ok

.. _filtering conformers:

Filtering conformers
--------------------

:meth:`.Tesliper.extract` will read and parse files it thinks are output files of the
quantum chemical software and update a :attr:`.Tesliper.conformers` internal data
storage. It is a ``dict``-like :class:`.Conformers` instance, that stores data for each
conformer in a form of an ordinary :class:`dict`. This inner dict uses :term:`genre`
names as keys and data as values (the form of which depends on the genre itself).
:class:`.Conformers` provide a number of methods for filtering conformers it knows,
allowing to easily hide data that should excluded from further analysis. ``tesliper``
calls this process a *trimming*. The middle part of the first code snippet are example
of trimming conformers:

.. code-block:: python

    tslr.conformers.trim_non_normal_termination()
    tslr.conformers.trim_not_optimized()
    tslr.conformers.trim_imaginary_frequencies()
    tslr.conformers.trim_to_range("gib", maximum=10, attribute="deltas")
    tslr.conformers.trim_rmsd(threshold=1.0, window_size=0.5, energy_genre="gib")

As you may suspect, :meth:`~.Conformers.trim_non_normal_termination` hides data from
calculations that did not terminate normally, :meth:`~.Conformers.trim_not_optimized`
hides data from conformers that are not optimized, and
:meth:`~.Conformers.trim_imaginary_frequencies` hides data from conformers that have at
least one imaginary frequency. More trimming methods is described :ref:`below
<trimming>`.

Conformers hidden are :term:`not kept <kept>`.
Information about which conformers are *kept* and *not kept* is stored in
:attr:`.Conformers.kept` attribute, which may also be manipulated more directly. More on
this topic will be :ref:`explained later <manipulating kept>`.

As mentioned earlier, :class:`Tesliper.conformers <.Conformers>` is a dict-like
structure, and as such offers a typical functionality of Python's `dict`\s. However,
checking for presence with ``conf in tslr.conformers`` or requesting a view with
standard :meth:`~dict.keys`, :meth:`~dict.values`, or :meth:`~dict.items` will operate
on the whole data set, ignoring any trimming applied earlier. :class:`.Conformers` class
offers additional :meth:`~.Conformers.kept_keys`, :meth:`~.Conformers.kept_values`, and
:meth:`~.Conformers.kept_items` methods, that return views that acknowledge trimming.

.. _trimming:

Trimming methods
''''''''''''''''

There is a number of those methods available for you, beside those mentioned above.
Below you will find them listed with a short summary and a link to a more comprehensive
explanation in the method's documentation.

:meth:`~.Conformers.trim_incomplete`
    Filters out conformers that doesn't contain data for as many expected genres as
    other conformers.

:meth:`~.Conformers.trim_imaginary_frequencies`
    Filters out conformers that contain imaginary frequencies (any number of negative
    frequency values).

:meth:`~.Conformers.trim_non_matching_stoichiometry`
    Filters out conformers that have different stoichiometry than expected.

:meth:`~.Conformers.trim_not_optimized`
    Filters out conformers that failed structure optimization.

:meth:`~.Conformers.trim_non_normal_termination`
    Filters out conformers, which calculation job did not terminate normally (was
    erroneous or interrupted).

:meth:`~.Conformers.trim_inconsistent_sizes`
    Filters out conformers that have iterable data genres in different size than most
    conformers. Helpful when :exc:`.InconsistentDataError` occurs.

:meth:`~.Conformers.trim_to_range`
    Filters out conformers that have a value of some specific data or property outside
    of the given range, e.g. their calculated population is less than 0.01.

:meth:`~.Conformers.trim_rmsd`
    Filters out conformers that are identical to another conformer, judging by a given
    threshold of the root-mean-square deviation of atomic positions (RMSD).

:meth:`~.Conformers.select_all`
    Marks all conformers as :term:`kept`.

:meth:`~.Conformers.reject_all`
    Marks all conformers as :term:`not kept <kept>`.

.. _manipulating kept:

Manipulating ``Conformers.kept``
''''''''''''''''''''''''''''''''

Information, which conformer is :term:`kept` and which is not, is stored in the
:attr:`Conformers.kept` attribute. It is a list of booleans, one for each conformer
stored, defining which conformers should be processed by ``tesliper``.

.. code-block:: python

    # assuming "conf_two" has imaginary frequencies
    tslr.conformers.trim_imaginary_frequencies()
    tslr.conformers.kept == [True, False, True]  # True
    tslr.export_data(["genres", "to", "export"])
    # only files for "conf_one" and "conf_three" are generated

:attr:`.Conformers.kept` may be modified using trimming methods described :ref:`earlier
<trimming>`, but also more directly: by setting it to a new value. Firstly, it is the
most straightforward to just assign a new list of boolean values to it. This list should
have the same number of elements as the number of conformers contained. A
:exc:`ValueError` is raised if it doesn't.

.. code-block:: python

    >>> tslr.conformers.kept
    [True, True, True]
    >>> tslr.conformers.kept = [False, True, False]
    >>> tslr.conformers.kept
    [False, True, False]
    >>> tslr.conformers.kept = [False, True, False, True]
    Traceback (most recent call last):
    ...
    ValueError: Must provide boolean value for each known conformer.
    4 values provided, 3 excepted.

Secondly, list of filenames of conformers intended to be *kept* may be given. Only these
conformers will be *kept*. If given filename is not in the underlying
:class:`tslr.conformers <.Conformers>`' dictionary, :exc:`KeyError` is raised.

.. code-block:: python

    >>> tslr.conformers.kept = ['conf_one']
    >>> tslr.conformers.kept
    [True, False, False]
    >>>  tslr.conformers.kept = ['conf_two', 'other']
    Traceback (most recent call last):
    ...
    KeyError: Unknown conformers: other.

Thirdly, list of integers representing conformers' indices may be given.
Only conformers with specified indices will be *kept*. If one of given integers
can't be translated to conformer's index, IndexError is raised. Indexing with
negative values is not supported currently.

.. code-block:: python

    >>> tslr.conformers.kept = [1, 2]
    >>> tslr.conformers.kept
    [False, True, True]
    >>> tslr.conformers.kept = [2, 3]
    Traceback (most recent call last):
    ...
    IndexError: Indexes out of bounds: 3.

Fourthly, assigning ``True`` or ``False`` to this attribute will mark all
conformers as *kept* or *not kept* respectively.

.. code-block:: python

    >>> tslr.conformers.kept = False
    >>> tslr.conformers.kept
    [False, False, False]
    >>> tslr.conformers.kept = True
    >>> tslr.conformers.kept
    [True, True, True]

.. warning::

    List of *kept* values may be also modified by setting its elements to ``True`` or
    ``False``. It is advised against, however, as a mistake such as
    ``tslr.conformers.kept[:2] = [True, False, False]`` will break some functionality by
    forcibly changing size of :attr:`tslr.conformers.kept <.Conformers.kept>` list.

Trimming temporarily
''''''''''''''''''''

:class:`.Conformers` provide two convenience context managers for temporarily trimming
its data: :attr:`~.Conformers.untrimmed` and :meth:`~.Conformers.trimmed_to`. The first
one will simply undo any trimming previously done, allowing you to operate on the full
data set or apply new, complex trimming logic. When Python exits
:attr:`~.Conformers.untrimmed` context, previous trimming is restored.

.. code-block:: python

    >>> tslr.conformers.kept = [False, True, False]
    >>> with tslr.conformers.untrimmed:
    >>>     tslr.conformers.kept
    [True, True, True]
    >>> tslr.conformers.kept
    [False, True, False]

The second one temporarily applies an arbitrary trimming, provided as a parameter to the
:meth:`~.Conformers.trimmed_to` call. Any value normally accepted by :attr:`.Conformers.kept`
may be used here.

.. code-block:: python

    >>> tslr.conformers.kept = [True, True, False]
    >>> with tslr.conformers.trimmed_to([1, 2]):
    >>>     tslr.conformers.kept
    [False, True, True]
    >>> tslr.conformers.kept
    [True, True, False]


.. tip::

    To trim conformers temporarily without discarding a currently applied trimming, you
    may use:

    .. code-block:: python

        with tslr.conformers.trimmed_to(tslr.conformers.kept):
            ...  # temporary trimming upon the current one


Simulating spectra
------------------

To calculate a simulated spectra you will need to have spectral activities extracted.
These will most probably come from a *freq* or *td* Gaussian calculation job, depending
on a genre of spectra you would like to simulate. ``tesliper`` can simulate IR, VCD, UV,
ECD, Raman, and ROA spectra, given the calculated values of conformers' optical
activity. When you call :meth:`.Tesliper.calculate_spectra` without any parameters, it
will calculate spectra of all available genres, using default activities genres and
default parameters, and store them in the :attr:`.Tesliper.spectra` dictionary.

Calculation parameters
''''''''''''''''''''''

``tesliper`` uses `Lorentzian <https://en.wikipedia.org/wiki/Cauchy_distribution>`_ or
`Gaussian <https://en.wikipedia.org/wiki/Normal_distribution>`_ fitting function to
simulate spectra from corresponding optical activities values. Both of these require to
specify a desired width of peak, as well as the beginning, end, and step of the abscissa
(x-axis values). If not told otherwise, ``tesliper`` will use a default values for these
parameters and a default fitting function for a given spectra genre. These default
values are available *via* :attr:`.Tesliper.standard_parameters` and are as follows.

.. table:: Default calculation parameters

    +-----------+--------------------------------+--------------------------------+
    | Parameter |  IR, VCD, Raman, ROA           | UV, ECD                        |
    +===========+================================+================================+
    | width     | 6 [:math:`\mathrm{cm}^{-1}`]   | 0.35 [:math:`\mathrm{eV}`]     |
    +-----------+--------------------------------+--------------------------------+
    | start     | 800 [:math:`\mathrm{cm}^{-1}`] | 150 [:math:`\mathrm{nm}`]      |
    +-----------+--------------------------------+--------------------------------+
    | stop      | 2900 [:math:`\mathrm{cm}^{-1}`]| 800 [:math:`\mathrm{nm}`]      |
    +-----------+--------------------------------+--------------------------------+
    | step      | 2 [:math:`\mathrm{cm}^{-1}`]   | 1 [:math:`\mathrm{nm}`]        |
    +-----------+--------------------------------+--------------------------------+
    | fitting   | :func:`.lorentzian`            | :func:`.gaussian`              |
    +-----------+--------------------------------+--------------------------------+

You can change the parameters used for spectra simulation by altering values in the
:attr:`.Tesliper.parameters` dictionary. It stores a ``dict`` of parameters' values for
each of spectra genres ("ir", "vcd", "uv", "ecd", "raman", and "roa"). *start*, *stop*,
and *step* expect its values to by in :math:`\mathrm{cm}^{-1}` units for vibrational and
scattering spectra, and :math:`\mathrm{nm}` units for electronic spectra. *width*
expects its value to be in :math:`\mathrm{cm}^{-1}` units for vibrational and scattering
spectra, and :math:`\mathrm{eV}` units for electronic spectra. *fitting* should be a
callable that may be used to simulate peaks as curves, preferably one of:
:func:`.gaussian` or :func:`.lorentzian`.

.. code-block:: python

    # change parameters' values one by one 
    tslr.parameters["uv"]["step"] = 0.5
    tslr.parameters["uv"]["width"] = 0.5

    tslr.parameters["vcd"].update(  # or with an update
        {"start": 500, "stop": 2500, "width": 2}
    )

    # "fitting" should be a callable
    from tesliper import lorentzian
    tslr.parameters["uv"]["fitting"] = lorentzian


.. table:: Descriptions of parameters

    +-----------+----------------------+-------------------------------------------+
    | Parameter |  ``type``            | Description                               |
    +===========+======================+===========================================+
    | width     | ``float`` or ``int`` | the beginning of the spectral range       |
    +-----------+----------------------+-------------------------------------------+
    | start     | ``float`` or ``int`` | the end of the spectral range             |
    +-----------+----------------------+-------------------------------------------+
    | stop      | ``float`` or ``int`` | step of the abscissa                      |
    +-----------+----------------------+-------------------------------------------+
    | step      | ``float`` or ``int`` | width of the peak                         |
    +-----------+----------------------+-------------------------------------------+
    | fitting   | ``Callable``         | function used to simulate peaks as curves |
    +-----------+----------------------+-------------------------------------------+

.. warning::

    When modifying :attr:`.Tesliper.parameters` be careful to not delete any of the
    key-value pairs. If you need to revert to standard parameters' values, you can just
    reassign them to :attr:`.Tesliper.standard_parameters`. .. code-block:: python
        
        tslr.parameters["ir"] = {
        ...     "start": 500, "stop": 2500, "width": 2
        ... }  # this will cause problems!
        # revert to default values
        tslr.parameters["ir"] = tslr.standard_parameters["ir"]

Activities genres
'''''''''''''''''

Averaging spectra
'''''''''''''''''

Calculating single spectrum
'''''''''''''''''''''''''''

Comparing with experiment
-------------------------

Loading experimental spectra
''''''''''''''''''''''''''''

Adjusting calculated spectra
''''''''''''''''''''''''''''
