"""All core algorithms for data handling live here, along with some helpers.

This package implements functions used by ``tesliper`` to provide its core
functionality: comparing conformers, calculating spectra, averaging them, etc. It is
divided into few modules based on a field that given function is related to.
"""

from .atoms import Atom, atomic_number, symbol_of_element, validate_atoms
from .energies import (
    BOLTZMANN,
    calculate_deltas,
    calculate_min_factors,
    calculate_populations,
)
from .geometry import (
    calc_rmsd,
    center,
    drop_atoms,
    fixed_windows,
    get_triangular,
    get_triangular_base,
    is_triangular,
    kabsch_rotate,
    rmsd_sieve,
    stretching_windows,
    take_atoms,
)
from .intensities import (
    DEFAULT_ACTIVITIES,
    dip_to_ir,
    osc_to_uv,
    rot_to_ecd,
    rot_to_vcd,
)
from .spectra import (
    calculate_average,
    calculate_spectra,
    convert_band,
    count_imaginary,
    find_imaginary,
    find_offset,
    find_scaling,
    gaussian,
    idx_offset,
    lorentzian,
    unify_abscissa,
)
