from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize(
        [
            "create_postflop_range_database.pyx",
            "montecarlo_loop.pyx",
        ],
        compiler_directives={"language_level": "3"}
    )
)