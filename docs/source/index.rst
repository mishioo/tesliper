.. image:: /_static/banner.png

|

.. just a vertical space to separate banner and header

Welcome to tesliper's documentation!
====================================

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
Among listed ``tesliper`` is the only one that is open source
and allows to easily filter parsed data.

.. list-table:: How does ``tesliper`` fit into the market?
   :header-rows: 1
   
   *  -
      - Tesliper
      - SpecDis [1]_
      - CDspecTech [2]_
      - ComputeVOA [3]_
      - GaussView [4]_
      - ChemCraft [5]_
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
      - |cross|           
      - |cross|          
      - |cross|           
      - |cross|
   *  - Job File Creation
      - |check|        
      - |cross|          
      - |cross|           
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


References
----------

.. [1] **SpecDis**: T. Bruhn, A. Schaumlöffel, Y. Hemberger, G. Pescitelli,
   *SpecDis version 1.71*, Berlin, Germany, **2017**, http://specdis-software.jimdo.com
.. [2] **CDspecTech**: C. L. Covington, P. L. Polavarapu, Chirality, **2017**, 29, 5,
   p. 178, DOI: `10.1002/chir.22691 <https://doi.org/10.1002/chir.22691>`_
.. [3] **ComputeVOA**: E. Debie, P. Bultinck, L. A. Nafie, R. K. Dukor, BioTools Inc.,
   Jupiter, FL, **2010**, https://biotools.us/software-2
.. [4] **GaussView**: R. Dennington, T. A. Keith, J. M. Millam, Semichem Inc.,
   *GaussView version 6.1*, Shawnee Mission, KS, **2016**
.. [5] **ChemCraft**: https://www.chemcraftprog.com


.. toctree::
   :hidden:
   :caption: Introduction

   Home page <self>
   Installation <installation>
   Conventions and Terms <glossary>

.. toctree::
   :hidden:
   :caption: Tutorials

   Graphical interface <gui>
   Scripting basics <tutorial>
   Advanced guide <advanced>

.. toctree::
   :hidden:
   :caption: Reference

   Available data genres <genres>
   Math and Algorithms <math>
   API reference <_autosummary/tesliper>

.. toctree::
   :hidden:
   :caption: Appendix

   Change Log <changelog>
   Index <genindex>


.. |check| unicode:: U+2714
.. |cross| unicode:: U+2718
