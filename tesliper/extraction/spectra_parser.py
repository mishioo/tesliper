import numpy as np


class SpectraParser:

    def __init__(self):
        self.max_lines_omitted = 20

    def parse(self, filename, mode='txt', delimiter=None):
        arr = None
        if mode == 'txt':
            try:
                arr = np.loadtxt(
                    filename, delimiter=delimiter, usecols=(0, 1), unpack=True
                )
            except ValueError:
                for n in range(self.max_lines_omitted):
                    try:
                        arr = np.loadtxt(filename, delimiter=delimiter,
                                         usecols=(0, 1), unpack=True,
                                         skiprows=n)
                    except ValueError:
                        pass
                    finally:
                        if arr is None:
                            raise
            return arr
