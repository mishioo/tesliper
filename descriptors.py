import numpy as np
from math import pi, sqrt

        
class BaseDescr:
    '''Base class for numpy.ndarray-holding descriptors.
    '''      

    def __init__(self, name):
        self.name = name
        self.inst_name = '_{}'.format(name)
    
    def __get__(self, obj, objtype):
        if obj is None:
            # instance attribute accessed on class, return self
            return self
        elif getattr(obj, self.inst_name) is None:
            raise AttributeError("'{}' object has no attribute '{}'"\
                                 .format(objtype.__name__, self.name))
        elif not obj.trimming:
            return getattr(obj, self.inst_name)
        else:
            return getattr(obj, self.inst_name)[obj.trimmer.blade]
        
        
class StrTypeArray(BaseDescr):
        
    def __set__(self, obj, value):
        setattr(obj, self.inst_name, np.array(value, dtype=str))
        
        
class IntTypeArray(BaseDescr):
        
    def __set__(self, obj, value):
        setattr(obj, self.inst_name, np.array(value, dtype=int))
        
        
class FloatTypeArray(BaseDescr):
        
    def __set__(self, obj, value):
        setattr(obj, self.inst_name, np.array(value, dtype=float))
        
        
class BladeDescr:

    def __init__(self):
        self.name = 'blade'
    
    def __get__(self, obj, objtype):
        if obj is None:
            return self
        if obj._blade is None:
            obj._blade = np.ones(obj.owner.true_size, dtype=bool)
        return obj._blade

    def __set__(self, obj, value):
        obj._blade = np.array(value, dtype=bool)
        
class IntensityArray:

    def __init__(self):
        self.name = 'intensities'
    
    def __get__(self, obj, objtype):
        if obj is None:
            # instance attribute accessed on class, return self
            return self
        else:
            get_inten = self.intensity_ref[obj.spectra_name]
            intensities = obj.values * get_inten(obj)
            print(obj.values.min(), obj.values.max())
            return intensities
            if not obj.trimming:
                return intensities
            else:
                return intensities[obj.trimmer.blade]

    @property
    def intensity_ref(self):
        def raman(obj):
            f = 9.695104081272649e-08
            e = 1 - np.exp(-14387.751601679205 * obj.frequencies / obj.t)
            return f * (obj.laser - obj.frequencies) ** 4 / (obj.frequencies * e)
        r = dict(
            raman = raman,
            roa = raman,
            ir = lambda obj: obj.frequencies / 91.48,
            vcd = lambda obj: obj.frequencies / 2.296e5,
            uv = lambda obj: obj.frequencies * 2.87e4,
            ecd = lambda obj: obj.frequencies / 22.96
            )
        return r

