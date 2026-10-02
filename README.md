# sphinxfortran_ng

[![PyPI](https://img.shields.io/pypi/v/sphinxfortran-ng.svg)](https://pypi.org/project/sphinxfortran-ng)
[![api docs](https://img.shields.io/static/v1?label=API&message=documentation&color=734f96&logo=read-the-docs&logoColor=white&style=flat-square)](https://scifortran.github.io/sphinxfortran_ng/)

An improved version of the original sphinx-fortran python module.

This code is based on the following original software:

- [sphinx-fortran](https://gitlab.com/l_sim/sphinx-fortran), on the "l_sim" working branch
- [sphinx-fortran](https://pypi.org/project/sphinx-fortran/), original sphinx-fortran project
- [crackfortran](https://github.com/numpy/numpy/tree/main/numpy/f2py) from the Numpy/f2py python module




## Documentation

The full documentation lives in the `doc` folder and on [GitHub pages](https://scifortran.github.io/sphinxfortran_ng/):

```console
pip install -r doc/requirements.txt
sphinx-build -b html doc doc/_build/html
```

| Page | Content |
|------|---------|
| `quickstart.rst` | Installation, `conf.py`, first build |
| `how_to_comment.rst` | How to write the Fortran comments (read this first) |
| `fortran_autodoc.rst` | The `f:auto*` directives, options, configuration values |
| `fortran_domain.rst` | Manual directives, field lists, roles, cross-references |
| `examples.rst`, `example_sf_arrays.rst`, `example_ed_input_vars.rst` | Worked examples on `SF_ARRAYS` and `ED_INPUT_VARS` |
| `api.rst` | Python API (`F90toRst`, domain classes) |
| `limitations.rst` | Known limitations and workarounds |

After editing a Fortran file, rebuild with `sphinx-build -E ...`: the sources
are not registered as dependencies of the pages.
