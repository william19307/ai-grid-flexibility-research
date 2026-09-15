"""Decode reviewed legacy scientific pickles without importing legacy pandas.

Only a small explicit constructor allowlist is accepted. Pandas objects are
captured as inert states; no arbitrary globals, persistent IDs or extension
opcodes are accepted. This is a source-specific reader, not a general sandbox.
"""
import io,pickle,pickletools,datetime
import numpy as np

class State:
    def __init__(self,*args,**kwargs):self.args=args;self.kwargs=kwargs
    def __setstate__(self,state):self.state=state

def index_state(cls,attrs):
    value=State();value.state=attrs;return value

PANDAS_TYPES={
 ('pandas.core.frame','DataFrame'),('pandas.core.series','Series'),
 ('pandas.core.internals','BlockManager'),('pandas.core.internals','SingleBlockManager'),
 ('pandas.core.indexes.base','Index'),('pandas.core.indexes.range','RangeIndex'),
 ('pandas.core.indexes.numeric','Int64Index'),('pandas.core.indexes.datetimes','DatetimeIndex')}
GLOBALS={('numpy.core.multiarray','_reconstruct'):np._core.multiarray._reconstruct,
 ('numpy','ndarray'):np.ndarray,('numpy','dtype'):np.dtype,
 ('builtins','slice'):slice,('datetime','timedelta'):datetime.timedelta,
 ('pandas.core.indexes.base','_new_Index'):index_state,
 ('pandas.core.indexes.datetimes','_new_DatetimeIndex'):index_state,
 ('pandas.tseries.offsets','Day'):State}

class Reader(pickle.Unpickler):
    def find_class(self,module,name):
        if (module,name) in PANDAS_TYPES:return State
        if (module,name) in GLOBALS:return GLOBALS[module,name]
        raise ValueError(('Unapproved legacy pickle global',module,name))
    def persistent_load(self,pid):raise ValueError('Persistent pickle IDs are unsupported')

def load(path):
    data=path.read_bytes()
    for op,arg,pos in pickletools.genops(data):
        if op.name in {'EXT1','EXT2','EXT4','PERSID','BINPERSID'}:raise ValueError(('Unsupported opcode',op.name))
    return Reader(io.BytesIO(data)).load()

def describe(obj,depth=0):
    if depth>6:return type(obj).__name__
    if isinstance(obj,State):return {'state':describe(getattr(obj,'state',None),depth+1),'args':describe(getattr(obj,'args',None),depth+1)}
    if isinstance(obj,np.ndarray):return {'array_shape':obj.shape,'dtype':str(obj.dtype),'first_values':obj.ravel()[:4].astype(str).tolist()}
    if isinstance(obj,dict):return {str(k):describe(v,depth+1) for k,v in obj.items()}
    if isinstance(obj,(list,tuple)):return [describe(v,depth+1) for v in obj]
    return repr(obj)

if __name__=='__main__':
    from pathlib import Path
    import json
    base=Path('work/research/sources/zenodo_13987282/selected/data/hydro')
    for p in base.glob('*.pickle'):
        print(p.name,json.dumps(describe(load(p)),ensure_ascii=False))
