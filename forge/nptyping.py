"""Minimal shim for `nptyping` so CadQuery imports on Python 3.14.

The real `nptyping` fails to build on 3.14, and CadQuery only uses it for type ANNOTATIONS in its sketch
constraint solver (`occ_impl/sketch_solver.py`: `NDArray`, `Float`). We do solid modelling + STEP/STL
export, not sketch-constraint solving, so annotation-only stubs are sufficient. Kept on the forge path so
`import cadquery` finds this before site-packages.
"""


class _Annotatable:
    def __class_getitem__(cls, item):     # support NDArray[...] / Float[...] subscripts in annotations
        return cls


class NDArray(_Annotatable):
    pass


class Float(_Annotatable):
    pass


class Int(_Annotatable):
    pass


class Shape(_Annotatable):
    pass
