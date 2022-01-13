Math and Algorithms
===================

.. |ith| replace:: :math:`i`:superscript:`th`

Simulation of spectra
---------------------

To simulate a spectrum, each band's theoretical signal intensity, derived from quantum
chemical calculations of corresponding optical activity, must be expressed as a
broadened peak, instead of the single scalar value. To simulate peak's shape one of the
curve fitting functions is used. ``tesliper`` implements two, most commonly used, such
functions: gaussian function [#gaussian]_ and lorentzian function [#lorentzian]_.

For each point on the simulated spectrum's abscissa, the corresponding signal intensity
is calculated by applying the fitting function to all bands of the conformer and summing
resulting values.

.. [#gaussian] https://mathworld.wolfram.com/GaussianFunction.html
.. [#lorentzian] https://mathworld.wolfram.com/LorentzianFunction.html

Gaussian fitting function
'''''''''''''''''''''''''

.. math::

    f(\nu) = \frac{1}{\sigma\sqrt{2\pi}}\sum\limits_i I_i e^{
        -(\nu_i - \nu)^2 / (2\sigma^2)
    }

:math:`\nu`
    Arbitrary point on the :math:`x`-axis, for which the signal intensity is calculated.
:math:`\nu_i`
    Point on the :math:`x`-axis, at which the |ith| band occur.
:math:`I_i`
    Intensity of the |ith| band.
:math:`\sigma = \sqrt{2}\omega`
    Standard derivation, in this context interpreted as equal to :math:`\sqrt{2}`
    times :math:`\omega`.
:math:`\omega`
    Half width of the peak at :math:`\frac{1}{e}` of its maximum value (HW1OeM),
    expressed in the :math:`x`-axis units.

Lorentzian fitting function
'''''''''''''''''''''''''''

.. math::

    f(\nu) = \frac{\gamma}{\pi}\sum\limits_i\frac{I_i}{(\nu_i - \nu)^2 + \gamma^2}

:math:`\nu`
    Arbitrary point on the :math:`x`-axis, for which the signal intensity is calculated.
:math:`\nu_i`
    Point on the :math:`x`-axis, at which the |ith| band occur.
:math:`I_i`
    Intensity of the |ith| band.
:math:`\gamma`
    Half width of the peak at half of its maximum value (HWHM),
    expressed in the :math:`x`-axis units.

Calculation of intensities
--------------------------

Dipole strength to IR intensities
'''''''''''''''''''''''''''''''''

Rotator strength to VCD intensities
'''''''''''''''''''''''''''''''''''

Oscillator strength to UV intensities
'''''''''''''''''''''''''''''''''''''

Dipole strength to UV intensities
'''''''''''''''''''''''''''''''''

Rotator strength to ECD intensities
'''''''''''''''''''''''''''''''''''

Raman/ROA intensities
'''''''''''''''''''''


Population of conformers
------------------------

Population of conformers is calculated according to the Boltzmann probability
distribution that "gives the probability that a system will be in a certain state as a
function of that state's energy and the temperature of the system." [#boltzmann]_ In
this context each conformer is considered one of the possible states of the system (a
studied molecule).

Firstly, we calculate a Boltzmann factors for each conformer in respect to the most
stable conformer (the one of the lowest energy). Boltzmann factor of two states is
defined as:

.. math::

    B^a_b = \frac{F(state_a)}{F(state_b)} = e^{(E_b - E_a)/kt}

where:

:math:`E_a` and :math:`E_b`
    energies of states :math:`a` and :math:`b`;
:math:`k = 0.0019872041 \: \mathrm{kcal/(mol*K)}`
    Boltzmann constant;
:math:`t` 
    temperature of the system.

Boltzmann factor represents a ratio of probabilities of the two states being occupied.
In other words, it shows how much more likely it is for the molecule to take the form of
one conformer over another conformer. Having a ratio of these probabilities for each
possible conformer in respect to the most stable conformer, we are able to find the
distribution of conformers (probability of taking the form of each conformer):

.. math::

    p_i = \frac{B_0^i}{\sum\limits_j^{states}B_0^j}

assuming that :math:`state_0` is the state of the lowest energy (the most stable
conformer).

.. [#boltzmann] https://en.wikipedia.org/wiki/Boltzmann_distribution

RMSD of conformers
------------------

Finding minimized value of RMSD
'''''''''''''''''''''''''''''''

Zero-centring atomic coordinates
""""""""""""""""""""""""""""""""

Rotating with Kabsch algorithm
""""""""""""""""""""""""""""""

Calculating RMSD of atomic positions
""""""""""""""""""""""""""""""""""""

Comparing conformers
''''''''''''''''''''

Moving window mechanism
"""""""""""""""""""""""

The sieve
"""""""""


Spectra transformation
----------------------

Finding common abscissa
'''''''''''''''''''''''

Finding best shift
''''''''''''''''''

Finding optimal scaling
'''''''''''''''''''''''


Other conversions
-----------------
