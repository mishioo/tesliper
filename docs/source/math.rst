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

RMSD, or root-mean-square deviation of atomic positions, is used as a measure of
similarity between two conformers. As its name hints, it is an average distance between
atoms in the two studied conformers: the lower the RMSD value, the more similar are
conformers in question.

Finding minimized value of RMSD
'''''''''''''''''''''''''''''''

In a typical output of the quantum chemical calculations software, molecule is
represented by a number of points (mapping to particular atoms) in a 3-dimensional
space. Usually, orientation and position of the molecule in the coordinate system is
arbitrary and simple overlay of the two conformers may not be the same as their optimal
overlap. To neglect the effect of conformers' rotation and shift on the similarity
measure, we will look for the common reference frame and optimal alignment of atoms.

Zero-centring atomic coordinates
""""""""""""""""""""""""""""""""

To find the common reference frame for two conformers we move both to the origin of the
coordinate system. This is done by calculating a centroid of a conformer and subtracting
it from each point representing an atom. The centroid is given as an arithmetic mean
of all the atoms in the conformer:

.. math::

    a^0_i = a_i - \frac{1}{n}\sum\limits_{j=a}^{n}a_j

where:

:math:`a_i`, :math:`a_j`
    atom's original position in the coordinate system;
:math:`a^0_i`
    atom's centered position in the coordinate system;
:math:`n`
    number of atoms in the molecule.

Rotating with Kabsch algorithm
""""""""""""""""""""""""""""""

Optimal rotation of one conformer onto another is achieved using a Kabsch algorithm
[#kabsch]_ (also known as Wahba's problem [#wanba]_). Interpreting positions of each
conformers' atoms as a matrix, we find the covariance matrix :math:`H` of these
matrices (:math:`P` and :math:`Q`):

.. math::

    H = P^\intercal Q

and then we use the singular value decomposition (SVD) [#svd]_ routine to get :math:`U`
and :math:`V` unitary matrices.

.. math::

    H = U \Sigma V ^\intercal

Having these, we can calculate the optimal rotation matrix as:

.. math::

    R = V \begin{pmatrix}1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & d\end{pmatrix} U ^\intercal

where :math:`d = \mathrm{sign}(\mathrm{det}(VU^\intercal))` that allows to ensure a
right-handed coordinate system.

.. note::

    To allow for calculation of th best rotation between sets of molecules and to
    compromise between efficiency and simplicity of implementation, ``tesliper`` uses
    Einstein summation convention [#einsum]_ *via* :func:`numpy.einsum` function. The
    implementation is as follows:

    .. literalinclude:: ../../tesliper/datawork/geometry.py
        :language: python
        :pyobject: kabsch_rotate
        :lines: 1-11,23,25-
        :emphasize-lines: 19,32

.. [#kabsch] https://en.wikipedia.org/wiki/Kabsch_algorithm
.. [#wanba] https://en.wikipedia.org/wiki/Wahba%27s_problem
.. [#svd] https://en.wikipedia.org/wiki/Singular_value_decomposition
.. [#einsum] https://en.wikipedia.org/wiki/Einstein_notation

Calculating RMSD of atomic positions
""""""""""""""""""""""""""""""""""""

Once conformers are aligned, the value of RMSD [#rmsd]_ is calculated simply by finding
a distance between each equivalent atoms and averaging their squares and finding the
root of this average:

.. math::

    \mathrm{RMSD} = \sqrt{\frac{1}{n}\sum\limits_i^n(p_i - q_i)^2}

where:

:math:`p_i` and :math:`q_i`
    positions of |ith| equivalent atoms in conformers :math:`P` and :math:`Q`;
:math:`n`
    number of atoms in each conformer.

.. [#rmsd] https://en.wikipedia.org/wiki/Root-mean-square_deviation_of_atomic_positions

Comparing conformers
''''''''''''''''''''

To compare conformers as efficiently as possible, the RMSD values are calculated not
in the each-to-each scheme, but inside a rather small moving window. The size of this
window determines how many calculations will be done for the whole collection.

Moving window mechanism
"""""""""""""""""""""""

``tesliper`` provides three types of moving windows: a :func:`fixed
<.geometry.fixed_windows>`, :func:`stretching <.geometry.stretching_windows>`, and
:func:`pyramid <.geometry.pyramid_windows>` windows. The strategy you choose will affect
both the performance and the accuracy of the RMSD sieve, as described below.

:func:`fixed <.geometry.fixed_windows>`
    The most basic sliding window of a fixed size. Provides the most control over the
    performance of the sieve, but is the least accurate.
:func:`stretching <.geometry.stretching_windows>`
    The default, allows to specify the size of the window in the context of some numeric
    property, usually the energy of conformers. The size may differ in the sense of the
    number of conformers in each window, but the difference between maximum and minimum
    values of said property inside a window will not be bigger than the given *size*.
    Provides a best compromise between the performance and the accuracy.
:func:`pyramid <.geometry.pyramid_windows>`
    The first window will contain the whole collection and each consecutive window will
    be smaller by one conformer. Allows to perform a each-to-each comparison, but in
    logarithmic time rather than quadratic time. Best accuracy but worst performance.

.. note::

    The actual windows produced by sliding window functions are iterables of
    :class:`numpy.ndarray`\s of indices (that point to the value in the original
    array of conformers).

The sieve
"""""""""

The :func:`RMSD sieve function <.geometry.rmsd_sieve>` takes care of zero-centring and
finding the best overlap of the conformers, as described previously. Aside form this, it
works as follows: for each window, provided by one of the moving window functions
described above, it takes the first conformer in the window (reference) and calculates
it's minimum RMSD value with respect to each of the other conformers in this window. Any
conformers that have lower RMSD value than a given threshold, will be considered
identical to the reference conformer and internally marked as :term:`not kept <kept>`.
The sieve returns an array of boolean value for each conformer: ``True`` if conformer's
structure is "original" and should be kept, ``False`` if it is a duplicate of other,
"original" structure (at least according to threshold given), and should be discarded.

Spectra transformation
----------------------

Finding best shift
''''''''''''''''''

Optimal offset of two spectra is determined by calculating their cross-correlation\
[#cross-corr]_ (understood as in the signal processing context) and finding its maximum
value. Index of this max value of the discrete cross-correlation array indicates the
position of one spectrum in respect to the other spectrum, in which the overlap of the
two is the greatest.

.. [#cross-corr] https://en.wikipedia.org/wiki/Cross-correlation

Finding optimal scaling
'''''''''''''''''''''''

Optimal scaling factor of spectra is determined by comparing a mean *y* values of target
spectrum and a reference spectrum.

