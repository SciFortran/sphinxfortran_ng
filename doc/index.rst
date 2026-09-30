sphinxfortran_ng
================

.. sidebar:: sphinxfortran_ng 0.6.0

      .. image:: _static/pictures/logo_github.png
         :width: 75%
         :align: center
         :target: https://github.com/SciFortran/sphinxfortran_ng

``sphinxfortran_ng`` is a Sphinx extension that provides a Fortran domain
and an autodoc-like mechanism for documenting Fortran source code.

It allows Fortran modules, subroutines, functions, variables, and derived
types to be documented directly from source files, using familiar
Sphinx directives and roles.

The extension is designed to integrate naturally with standard Sphinx
workflows and follows the conventions of ``sphinx.ext.autodoc`` where
possible. It is an improved version of the original ``sphinx-fortran``
project, whose parser is itself a trimmed copy of the ``crackfortran``
module of NumPy/f2py.


Features
--------

- Fortran domain (``f:``) with directives and cross-referencing roles
- Autodoc-style directives (``f:automodule``, ``f:autoroutine``, ...) for
  Fortran source code
- Extraction of documentation from ordinary Fortran comments, written in
  reStructuredText, with **no special comment marker** required
- Argument types, shapes, ``intent``, optional arguments and default values
  are read from the declarations, so they never get out of sync with the code
- Support for modern Fortran (90 and later): modules, derived types,
  generic interfaces, ``bind(c)`` variables, ``use ... only`` renaming
- Clean integration with HTML, LaTeX, and other Sphinx builders


How it works
------------

Documenting a Fortran module involves three cooperating stages:

1. **Parsing** -- at the ``builder-inited`` event, every file found through
   ``fortran_src`` is parsed by :mod:`sphinxfortran_ng.crackfortran_for_sphinx`
   and its comments are attached to the parsed blocks by
   :class:`~sphinxfortran_ng.fortran_autodoc.F90toRst`.
2. **Generation** -- when an ``f:auto*`` directive is met, ``F90toRst``
   converts the requested object into plain reStructuredText that uses the
   manual ``f:module``, ``f:function``, ``f:variable``, ... directives, and
   inserts it in the document.
3. **Rendering** -- the directives of the Fortran domain
   (:class:`~sphinxfortran_ng.fortran_domain.FortranDomain`) turn that text
   into signatures, field lists, index entries and cross-reference targets.

The two halves are documented separately: :doc:`fortran_autodoc` (stages 1
and 2) and :doc:`fortran_domain` (stage 3). Because stage 2 produces text
that stage 3 understands, everything the autodoc directives can do can also
be written by hand.


A first example
---------------

Given this Fortran source, in which the documentation is written as plain
comments **right after the declaration line** it describes:

.. code-block:: fortran

   module sf_arrays
   !SciFortran module for array creation and manipulation
     implicit none
   contains

     function arange(start,num) result(array)
     !
     !Returns an array of :f:var:`num` integers starting with :f:var:`start`
     !
       integer :: start       !First element of the array
       integer :: num         !Length of the array
       integer :: array(num)  !The integers in [:f:var:`start`, :f:var:`start` + :f:var:`num` - 1]
       integer :: i
       forall(i=1:num) array(i) = start+i-1
     end function arange

   end module sf_arrays

the two lines below are enough to document the module:

.. code-block:: rst

   .. f:automodule:: sf_arrays

which yields, for the function, the same result as writing by hand:

.. code-block:: rst

   .. f:function:: arange(start, num)

      Returns an array of :f:var:`num` integers starting with :f:var:`start`

      :p integer start: First element of the array
      :p integer num: Length of the array
      :r integer array(num): The integers in [:f:var:`start`, :f:var:`start` + :f:var:`num` - 1]

Note that ``:p`` / ``:r`` fields, the argument types and the shape
``array(num)`` were all produced from the declarations; only the sentences
were written by the author.

.. important::

   Module, routine and variable names are stored **in lower case** by the
   parser. Always write them in lower case in the directives:
   ``.. f:automodule:: sf_arrays``, not ``SF_ARRAYS``.


Where to go next
----------------

:doc:`quickstart`
   Install the extension, configure ``conf.py`` and build a first page.

:doc:`how_to_comment`
   **Start here when writing Fortran comments.** The exact rules the parser
   follows, with the pitfalls that make a description silently disappear.

:doc:`fortran_autodoc`
   The ``f:auto*`` directives, their options and the configuration values.

:doc:`fortran_domain`
   The manual directives, the field lists, the roles for cross-referencing
   and the module index.

:doc:`examples`
   Walk-through of two real modules: a library of functions (``SF_ARRAYS``)
   and a module made of input variables (``ED_INPUT_VARS``), with the
   generated reStructuredText, each followed by its live rendering.

:doc:`limitations`
   Known limitations and behaviours that differ from what one may expect,
   with workarounds.


Contents
--------

.. toctree::
   :maxdepth: 2

   quickstart
   how_to_comment
   fortran_autodoc
   fortran_domain
   examples
   limitations

