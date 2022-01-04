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
    └── vibrational
        ├── conf_one.out
        └── conf_two.out

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

.. TODO: add ``trimmed_keys`` etc.

.. _trimming:

Trimming methods
''''''''''''''''

There is a number of those methods available for you, beside those mentioned above.
Below you will find them listed with a short summary and a link to a more comprehensive
explanation in the method's documentation.

:meth:`~.Conformers.trim_incomplete`
    desc

:meth:`~.Conformers.trim_imaginary_frequencies`
    desc

:meth:`~.Conformers.trim_non_matching_stoichiometry`
    desc

:meth:`~.Conformers.trim_not_optimized`
    desc

:meth:`~.Conformers.trim_non_normal_termination`
    desc

:meth:`~.Conformers.trim_inconsistent_sizes`
    desc

:meth:`~.Conformers.trim_to_range`
    desc

:meth:`~.Conformers.trim_rmsd`
    desc

:meth:`~.Conformers.select_all`
    desc

:meth:`~.Conformers.reject_all`
    desc

.. TODO: add ``with trimmed_to`` etc.

.. _manipulating kept:

Manipulating ``Conformers.kept``
''''''''''''''''''''''''''''''''

