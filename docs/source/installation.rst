Installation
============

.. _install-gui:

GUI for Windows
---------------

For Windows users that only intend to use graphical interface, ``tesliper`` is available
as a standalone .exe application, available for download from the `latest release
<https://github.com/mishioo/tesliper/releases/latest/>`_ under the **Assets** section at
the bottom of the page. No installation is required, just double-click the downloaded
**Tesliper.exe** file to run the application.

Unfortunately, a single-file installation is not available for unix-like systems.
Please follow a terminal-based installation instructions below.

Install from terminal
---------------------

``tesliper`` is a Python package `distributed via PyPI <https://pypi.org/project/tesliper/>`_.
You can install it to your python distribution simply by running::

    python -m pip install tesliper

in your terminal. This will download and install ``tesliper`` along with it's essential
dependencies. A graphical interface have an additional dependency, but it may be
easily included in your installation if you use ``python -m pip install tesliper[gui]``
instead. Some users of unix-like systems may also need to instal ``tkinter`` manually,
if it is not included in their distribution by default. Please refer to relevant online
resources on how to do this in your system, if that is your case.

.. note::
    Reminder for zsh users to quote the braces like this ``'tesliper[gui]'``
    or like this ``tesliper\[gui]`` when installing extras. This is necessary, because
    normally zsh uses ``some[thing]`` syntax for pattern matching.

Requirements
------------

This software needs at least Python 3.6 to run. It also uses some additional packages::

    numpy
    openpyxl
    matplotlib (optional, for GUI)

.. note::
    ``tesliper`` uses ``tkinter`` to deliver the graphical interface. It is included in
    most Python distributions, but please be aware, that some might miss it. You will
    need to install it manually in such case.