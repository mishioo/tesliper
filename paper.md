---
title: "tesliper: a theoretical spectroscopist's little helper"
tags:
  - Python
  - chemistry
  - spectroscopy
  - Gaussian
  - chemical computing 
  - optical spectroscopy
  - spectral simulations
  - workflow automation
  - batch processing 
authors:
  - name: Michał M. Więcław^[corresponding author]
    orcid: 0000-0001-7884-8982
    affiliation: 1
affiliations:
 - name: Institute of Organic Chemistry, Polish Academy of Sciences
   index: 1
date: 26 January 2022
bibliography: paper.bib
---

# Summary
`tesliper` is a software for bulk processing of Gaussian (quantum chemistry calculations
software) output files regarding conformational search and spectra simulations.
Simulation of molecule's optical spectra usually requires structure optimization and
calculation of electronic properties of multiple conformers of the studied molecule.
Gaussian [@gaussian] is one of the commonly used software to perform such calculations
and `tesliper` was created to aid in handling and analysis of these calculations'
outcome.

It allows to easily exclude conformers that are not suitable for further analysis:
erroneous, not optimized, of higher energy or lower contribution than a desired
threshold. It also implements a geometry comparison feature: an RMSD sieve, enabling to
filter out similar structures. A theoretical IR, VCD, UV, ECD, Raman, and ROA spectra
may be calculated for individual conformers or as an population-weighted average.
Offering a graphical user interface and Python API, it is easily accessible by users'
preferred method of interaction with the computer: visual or textual.

# Statement of Need
Simulation of optical spectra of organic compounds becomes one of the routine tasks for
chemical analysts. For example, it is a necessary step in one of the increasingly
popular methods of establishing compound's absolute configuration, which compares its
recorded and simulated circular dichroism spectra. However, the process of obtaining a
simulated spectrum may be cumbersome, as it usually involves analyzing a large number of
potentially stable conformers of the studied molecule.

Several software capable of simulating a spectrum from Gaussian calculations are already
available, e.g. SpecDis [@specdis], CDspecTech [@cdspectech], ComputeVOA [@computevoa],
ChemCraft [@chemcraft], or GaussView [@gaussview]. However, each of these programs has
some severe limitations, for example they are not freely available (ComputeVOA,
ChemCraft, GaussView) or cannot simulate certain types of spectra (SpecDis, ComputeVOA,
ChemCraft). Other ones lack important features, like comparison of conformers' geometry
(SpecDis, CDspecTech, GaussView) or population-based spectra averaging (ComputeVOA,
ChemCraft, GaussView).

Even with adoption of one or more of the mentioned software, the process is often
suboptimal, incomplete, or not enough automated. Many research groups tackle this
problem with a home-brewed scripting solutions that are usually not easily adjusted or
extended, or with manual work, which may be extremely time consuming. There is a clear
need for a simple interface to automate tedious parts of the typical spectra simulation
workflow. `tesliper` aims to satisfy this need.

# Acknowledgements
Many thanks to the scientists, who advised me on the domain-specific details and helped
to test the software:

- Joanna Rode [ORCID iD 0000-0003-0592-4053](https://orcid.org/0000-0003-0592-4053)
- Magdalena Jawiczuk [ORCID iD 0000-0003-2576-4042](https://orcid.org/0000-0003-2576-4042)
- Marcin Górecki [ORCID iD 0000-0001-7472-3875](https://orcid.org/0000-0001-7472-3875)

# References

