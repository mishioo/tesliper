.. image:: /_static/banner.png
==============================

``tesliper`` is a package for batch processing of Gaussian output files, focusing on
extraction and processing of data related to simulation of optical spectra. The software
offers a Python API and a graphical user interface (GUI), allowing for your preferred
style of interaction with the computer: visual or textual. It's main goal is to minimize
time and manual work needed to simulate optical spectrum of investigated compound.

Key features
------------

``tesliper`` was designed for working with multiple conformers of a compound,
represented by a number of files obtained from Gaussian quantum-chemical computations
software. It allows you easily exclude conformers that are not suitable for further
analysis: erroneous, not optimized, of higher energy than a user-given threshold, or
very similar to some other structure in the set. Data parsed from files and data
calculated may be exported to other file formats for storage or further analysis with
other tools. Below is a quick overview of features it provides:

- Batch processing of Gaussian output files regarding structure optimization and
  simulation of spectral properties
- Conditional, property-based filtering of conformers
- Geometry comparison via the RMSD sieve
- Calculation of Boltzmann distribution—based populations of conformers
- Simulation of IR, VCD, UV, ECD, Raman, and ROA spectra from spectral activities
- Export of extracted and calculated data to .txt, .csv, and .xlsx file formats
- Export of .gjf files for further calculations in Gaussian software
- Free & open source (OSI approved BSD 2-Clause license)
- Graphical and programmatic interfaces
- Easily extendible with a little of Python knowledge

Motivation and context
----------------------

Simulation of optical spectra of organic compounds becomes one of the routine tasks
for chemical analysts -- it is a necessary step in one of the increasingly popular
methods of establishing compound's absolute configuration. However, the process
of obtaining a simulated spectrum may be cumbersome, as it usually involves analyzing
a large number of potentially stable conformers of the studied molecule.
``tesliper`` was created to aid in such work.

It should be noted that ``tesliper`` is not the only software that is capable of
providing a simulated spectrum, given output of quantum-chemical computations. The table
below summarizes other available GUI tools and compares features they offer.
Among listed ``tesliper`` is the only one that is open source, readily extendible,
and allows to easily filter parsed data.

.. list-table:: How ``tesliper`` fits into the market?
   :widths: 23 8 7 10 9 10 9
   :header-rows: 1
   
   *  -
      - Tesliper
      - SpecDis
      - CDspecTech
      - ComputeVOA
      - GaussView
      - ChemCraft
   *  - Free
      - |check|        
      - |check|          
      - |check|           
      - |cross|          
      - |cross|           
      - |cross|
   *  - Open Source
      - |check|        
      - |cross|          
      - |cross|           
      - |cross|          
      - |cross|           
      - |cross|
   *  - Batch Processing
      - |check|        
      - |check|          
      - |check|           
      - |cross|     
      - .gjf export
      - .gjf modif.
   *  - Geometry Comparison
      - |check|        
      - |cross|          
      - |cross|           
      - |check|          
      - |cross|           
      - |check|
   *  - Averaging
      - |check|        
      - |check|          
      - |check|           
      - |cross|          
      - |cross|           
      - |cross|
   *  - Conditional Filtering
      - |check|        
      - |cross|          
      - |check|           
      - |cross|          
      - |cross|           
      - |cross|
   *  - Job File Creation
      - |check|        
      - |cross|          
      - |check|           
      - |check|          
      - |check|           
      - |check|
   *  - Electronic Spectra
      - |check|        
      - |check|          
      - |check|           
      - |cross|          
      - |check|           
      - |cross|
   *  - Scattering Spectra
      - |check|        
      - |cross|          
      - |check|           
      - |check|          
      - |check|           
      - |check|
   *  - Multi-platform
      - |check|        
      - |check|          
      - |check|           
      - |cross|          
      - |check|       
      - needs wine
   *  - Conformational Search
      - |cross|        
      - |cross|          
      - |cross|           
      - |check|       
      - optional
      - |cross|
   *  - Molecule Visualization
      - |cross|       
      - |cross|          
      - |cross|           
      - |check|          
      - |check|           
      - |check|   

.. TODO: add references to other software

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   Home page <self>
   Installation <installation>
   Graphical interface <gui>
   Scripting basics <tutorial>
   Extending ``tesliper`` <extend>
   API reference <_autosummary/tesliper>

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. |check| unicode:: U+2714
.. |cross| unicode:: U+2718
