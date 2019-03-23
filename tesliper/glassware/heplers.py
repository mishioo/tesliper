from .array_base import ArrayProperty


class SingleSpectrum:

    _vibra_units = {
        'width': 'cm-1',
        'start': 'cm-1',
        'stop': 'cm-1',
        'step': 'cm-1',
        'x': 'Frequency / cm^(-1)'
    }
    _electr_units = {
        'width': 'eV',
        'start': 'nm',
        'stop': 'nm',
        'step': 'nm',
        'x': 'Wavelength / nm'
    }
    _units = {
        'ir': {'y': 'Epsilon'},
        'uv': {'y': 'Epsilon'},
        'vcd': {'y': 'Delta Epsilon'},
        'ecd': {'y': 'Delta Epsilon'},
        'raman': {'y': 'I(R)+I(L)'},
        'roa': {'y': 'I(R)-I(L)'}
    }
    for u in 'ir vcd raman roa'.split(' '):
        _units[u].update(_vibra_units)
    for u in ('uv', 'ecd'):
        _units[u].update(_electr_units)

    def __init__(
            self, genre, values, abscissa, width=0.0, fitting='n/a',
            scaling=1.0, offset=0.0, filenames=None, averaged_by=None
    ):
        self.genre = genre
        self.filenames = [] if filenames is None else filenames
        self.averaged_by = averaged_by
        self.abscissa = abscissa
        self.values = values
        self.start = abscissa[0]
        self.stop = abscissa[-1]
        self.step = abs(abscissa[0] - abscissa[1])
        self.width = width
        self.fitting = fitting
        self.scaling = scaling
        self.offset = offset

    abscissa = ArrayProperty(check_against=None)
    values = ArrayProperty(check_against='abscissa')

    @property
    def units(self):
        return self._units[self.genre]

    @property
    def scaling(self):
        return self._scaling

    @scaling.setter
    def scaling(self, factor):
        self._scaling = factor
        self._y = self.values * factor

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, offset):
        self._offset = offset
        self._x = self.abscissa + offset

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    def __len__(self):
        return len(self.abscissa)

    def __bool__(self):
        return self.abscissa.size != 0
