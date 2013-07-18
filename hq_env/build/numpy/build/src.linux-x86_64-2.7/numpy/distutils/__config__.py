# This file is generated by /home/dmyung/src/commcarehq-venv/hq_env/build/numpy/-c
# It contains system_info results at the time of building this package.
__all__ = ["get_info","show"]

blas_info={'libraries': ['blas'], 'library_dirs': ['/usr/lib'], 'language': 'f77'}
lapack_info={'libraries': ['lapack'], 'library_dirs': ['/usr/lib'], 'language': 'f77'}
atlas_threads_info={}
blas_opt_info={'libraries': ['blas'], 'library_dirs': ['/usr/lib'], 'define_macros': [('NO_ATLAS_INFO', 1)], 'language': 'f77'}
atlas_blas_threads_info={}
lapack_opt_info={'libraries': ['lapack', 'blas'], 'library_dirs': ['/usr/lib'], 'define_macros': [('NO_ATLAS_INFO', 1)], 'language': 'f77'}
atlas_info={}
lapack_mkl_info={}
blas_mkl_info={}
atlas_blas_info={}
mkl_info={}

def get_info(name):
    g = globals()
    return g.get(name, g.get(name + "_info", {}))

def show():
    for name,info_dict in globals().items():
        if name[0] == "_" or type(info_dict) is not type({}): continue
        print(name + ":")
        if not info_dict:
            print("  NOT AVAILABLE")
        for k,v in info_dict.items():
            v = str(v)
            if k == "sources" and len(v) > 200:
                v = v[:60] + " ...\n... " + v[-60:]
            print("    %s = %s" % (k,v))
    