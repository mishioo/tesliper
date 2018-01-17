import numpy as np

        
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
