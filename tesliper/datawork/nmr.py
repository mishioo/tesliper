# IMPORTS
import logging as lgg
import numpy as np
from .helpers import atomicnum


# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# MODULE FUNCTIONS
def take_atoms(values, atoms, wanted):
    """Filters given values to those, corresponding to atoms of wanted type.
    Roughly equivalent to:
    >>> numpy.take(values, numpy.where(numpy.equal(atoms, wanted))[0], 1)
    but returns empty array, if no atom in 'atoms' matches 'wanted' atom.

    Parameters
    ----------
    values: list or numpy.array
        two- or tree-dimensional array of values of shape
        (conformers, values[, coordinates])
    atoms: list or numpy.array
        list of atoms in molecule; order should be the same as corresponding
        values for each conformer
    wanted: int
        atomic number of wanted atom
    """
    blade = np.equal(atoms, wanted)
    indices = np.where(blade)[0]
    if not indices.size:
        output = np.array([])
    else:
        try:
            output = np.take(values, indices, 1)
        except np.AxisError:
            output = np.take(values, indices, 0)
    return output
