Fortran Autodoc
===============

`sphinxfortran_ng` provides an autodoc-style extension for Fortran source
code. It automatically extracts documentation from Fortran files and
generates reStructuredText output describing modules, routines, variables,
and derived types.

The design and usage closely follow ``sphinx.ext.autodoc`` for Python. The
comment conventions that the sources must follow are described in
:doc:`how_to_comment`.

.. contents:: On this page
   :local:
   :depth: 2


Enabling the Extension
----------------------

Add the Fortran domain **and** autodoc extensions to your ``conf.py``. Both
are required: the domain creates the ``f:`` domain and the autodoc extension
adds the ``f:auto*`` directives to it.

.. code-block:: python

   extensions += [
       "sphinxfortran_ng.fortran_domain",
       "sphinxfortran_ng.fortran_autodoc",
   ]

Configure the Fortran source search path:

.. code-block:: python

   fortran_src = ["../src"]
   fortran_ext = ["f90", "F90", "f95", "F95"]

The sources are parsed **once**, when the builder is initialised
(:func:`~sphinxfortran_ng.fortran_autodoc.fortran_parse`). Sphinx logs
``parsing fortran sources... done``, or ``no fortran files found`` when
nothing matches, in which case every ``f:auto*`` directive silently produces
nothing.

.. _autodoc-config:

Configuration values
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 24 16 60

   * - Name
     - Default
     - Meaning
   * - ``fortran_src``
     - ``['.']``
     - List (or a single string) of files, glob patterns and directories.
       Directories are scanned for ``*.<ext>`` for every extension of
       ``fortran_ext``, in lower case, upper case and as written, but **not
       recursively**. Paths are made absolute and sorted.
   * - ``fortran_ext``
     - ``['f90', 'f95']``
     - Extensions looked for in the directories of ``fortran_src``. Files
       given explicitly or through a glob are taken whatever their extension.
   * - ``fortran_indent``
     - ``4``
     - Indentation used in the generated reST: a number of spaces, ``"tab"``
       or ``"space"`` (or any string). Any consistent indentation gives the
       same result; the default is fine.
   * - ``fortran_title_underline``
     - ``'-'``
     - Underline character of the titles generated in ``title`` subsection
       mode.
   * - ``fortran_encoding``
     - ``'utf8'``
     - Accepted for compatibility. It is currently **not** used: files are
       opened with the default encoding of Python.
   * - ``fortran_subsection_type``
     - ``'rubric'``
     - Registered, but currently **not** read: the subsection type is set by
       the ``:subsection_type:`` option of each ``f:automodule``.

The autodoc extension also registers the object types ``ftype`` and ``fvar``
(``:ftype:``, ``:fvar:``) which belong to the generic Sphinx object mechanism
and are independent of the ``f:`` domain.


Directives at a glance
----------------------

.. list-table::
   :header-rows: 1
   :widths: 26 74

   * - Directive
     - Documents
   * - ``f:automodule``
     - A whole module: description, quick access, used modules, types,
       variables, routines.
   * - ``f:automodvars``
     - Only the variables of a module (same options as ``f:automodule``).
   * - ``f:autoroutine``
     - One function, subroutine or generic interface.
   * - ``f:autofunction`` / ``f:autosubroutine``
     - One function / subroutine.
   * - ``f:autointerface``
     - See the caveat in :doc:`limitations`; prefer ``f:autoroutine``.
   * - ``f:autotype``
     - One derived type, with its components.
   * - ``f:autovariable``
     - One module variable.
   * - ``f:autoprogram``
     - One main program.
   * - ``f:autosrcfile``
     - Everything found in one source file.

Every argument is a **name in lower case** (the parser lower-cases the
names of the source). For the object directives the name of the module may
prefix it, separated by ``/``, and is ignored: ``mymodule/solve`` is the same
as ``solve``.


``.. f:automodule::``
---------------------

Document a Fortran ``module`` and optionally its contents.

The ``f:automodule`` directive takes a module found in the sources parsed at
start-up and generates documentation for the module itself and for the
entities it contains.

Syntax
~~~~~~

.. code-block:: rst

   .. f:automodule:: module_name
      :members: name1, name2
      :undoc-members: name3
      :forceadd-members: name4
      :include-private:
      :title_underline: -
      :subsection_type: rubric
      :indent: tab
      :hide-output: 1

Options
~~~~~~~

All options are optional, and every option takes effect **only for this
directive**: the previous configuration is restored at the end.

``:members:``
   Comma separated list of names. When it is given, **only** the listed
   variables, types and routines of the module are documented (a private
   entity is documented if it is explicitly listed). Without a value all the
   public members are documented.

``:undoc-members:``
   Comma separated list of names of members to **leave out**.

   .. note::

      Despite its name, and unlike the Python ``:undoc-members:``, this
      option does not switch the display of undocumented members on: those
      are always shown. It is the way to hide chosen members, for instance
      the internal variables ending in ``_`` of ``ED_INPUT_VARS``.

      Do not combine it with ``:members:``: when ``:undoc-members:`` is given,
      it is applied instead of the restriction of ``:members:``.

``:forceadd-members:``
   Comma separated list of names that are documented **whatever** their
   visibility and the other options. This is the way to document a member
   declared ``private`` in the module.

``:include-private:``
   Intended to include the ``private`` members.

   .. warning::

      In the current version this option has **no effect**: a bare option
      is read as an empty string, which is ignored, and any value given is
      stored as a non-``None`` string, which still excludes the private
      members. Use ``:forceadd-members:`` or ``:members:`` with explicit
      names instead. From Python, setting ``F90toRst.exclude_private = None``
      does include them.

``:title_underline:``
   Character used to underline the titles, when ``:subsection_type:`` is
   ``title``. Typical values are ``-``, ``~`` or ``^``. Ignored in ``rubric``
   mode.

``:subsection_type:``
   Control how the parts of a module (*Description*, *Quick access*,
   *Types*, *Variables*, *Subroutines and functions*, ...) are introduced.

   ``rubric``
      (default) Each part is introduced by a ``.. rubric::`` and does not
      appear in the table of contents.

   ``title``
      Each part is a real section, underlined with ``:title_underline:``. It
      then shows in the table of contents. The underline must be consistent
      with the heading hierarchy of the page that contains the directive.

   Any other value, ``section`` included, behaves like ``rubric``.

``:indent:``
   Indentation of the generated text. Only ``tab`` and ``space`` are
   understood; a number given here is **not** converted to spaces and would
   be used as the text of the indentation. Set the number of spaces once for
   all with ``fortran_indent`` in ``conf.py``.

``:hide-output:``
   Only declare the module (``f:module``) and produce none of its contents.
   The option must be given a value, for instance ``:hide-output: 1``, since
   an empty value is ignored. This is useful to register the module in the
   index and for cross references while the content is written by hand.

Generated layout
~~~~~~~~~~~~~~~~

The parts of a module, in this order, are: the ``f:module`` declaration (with
the synopsis); *Description*; *Quick access* (the lists of types, variables
and routines); *Used modules* and *External modules*; *Types*; *Variables*;
*Subroutines and functions*. A part that is empty is omitted. For
``SF_ARRAYS`` the head is:

.. code-block:: rst

   .. f:module:: sf_arrays
      :synopsis: SciFortran module for array creation and manipulation

   .. rubric:: Description

   SciFortran module for array creation and manipulation

   .. rubric:: Quick access

   :Routines: :f:func:`arange`, :f:func:`linspace`, :f:func:`logspace`, :f:func:`powspace`, :f:func:`upminterval`, :f:func:`upmspace`

With ``:subsection_type: title`` and ``:title_underline: -`` the same parts of
a small module become sections:

.. code-block:: rst

   .. f:module:: m
      :synopsis: Tiny module used to show the layout.

   Description
   -----------

   Tiny module used to show the layout.

   Quick access
   ------------

   :Variables: :f:var:`pi`
   :Routines: :f:func:`hello`

   Variables
   ---------

   .. f:variable:: pi

      Circle constant

      :Type: real

   Subroutines and functions
   -------------------------

   .. f:subroutine:: hello()

      Says hello.

and ``:hide-output: 1`` reduces the output to:

.. code-block:: rst

   .. f:module:: m
      :synopsis: Tiny module used to show the layout.

Example
~~~~~~~

.. code-block:: rst

   Array creation
   ==============

   .. f:automodule:: sf_arrays
      :subsection_type: title
      :title_underline: -

Document only two routines of a larger module:

.. code-block:: rst

   .. f:automodule:: ed_input_vars
      :members: ed_read_input, ed_update_input

Document a module without its internal helper variables (the ones ending in
``_`` in ``ED_INPUT_VARS``):

.. code-block:: rst

   .. f:automodule:: ed_input_vars
      :undoc-members: ed_twin_, ed_total_ud_, uloc_, pair_field_


``.. f:automodvars::``
----------------------

Document only the variables of a module. It accepts the same options as
``f:automodule`` (so ``:members:`` and ``:undoc-members:`` work) but writes
neither a module declaration nor any title: the output is the list of the
variables followed by their descriptions, to be placed under a heading of
your own.

.. code-block:: rst

   Input variables
   ---------------

   .. f:automodvars:: ed_input_vars

For a small module the output is:

.. code-block:: rst

   :f:var:`pi`

   .. f:variable:: pi

      Circle constant

      :Type: real

.. note::

   The variables are only registered under the module if an ``f:module``
   directive, or an ``f:automodule`` with ``:hide-output: 1``, has been
   written before.


``.. f:autoroutine::``
----------------------

Document a single Fortran subroutine, function or generic interface.

Syntax
~~~~~~

.. code-block:: rst

   .. f:autoroutine:: routine_name

The directive has **no option**. It extracts the routine signature, the
arguments with their types, shapes and attributes, and the description
comments, and inserts the corresponding ``f:function``, ``f:subroutine`` or
``f:interface`` directive, so ``f:autoroutine`` is the directive to use for
a generic interface.

``f:autofunction`` and ``f:autosubroutine`` are equivalent (the parser keeps
a single index of routines, so both find any of them; only the text of the
warning for an unknown name differs).

Example
~~~~~~~

.. code-block:: rst

   .. f:autoroutine:: linspace

which gives, for ``SF_ARRAYS``:

.. code-block:: rst

   .. f:function:: linspace(start, stop, num[, istart, iend, mesh])

      Returns an array of evenly spaced numbers over a specified interval.
      Returns :f:var:`num` evenly spaced samples, calculated over the interval [:f:var:`start`, :f:var:`stop`].
      The start and end points of the interval can optionally be excluded.

      :p real start: Starting value of the sequence
      :p real stop: End value of the sequence
      :p integer num: Number of samples to generate
      :o logical istart: If :code:`.true.`, :f:var:`start` is included in the resulting array. Default :code:`.true.`
      :o logical iend: If :code:`.true.`, :f:var:`stop` is included in the resulting array. Default :code:`.true.`
      :o real mesh: If present, the step is saved in this variable
      :r real array(num): Contains :f:var:`num` equally spaced samples in the interval [:f:var:`start`, :f:var:`stop`], left/right open or closed depending on :f:var:`istart` and :f:var:`iend`

If the name is not found, a warning is emitted (``Wrong routine name``,
``Wrong function name``, ...) and the directive then fails with an error.

.. note::

   Routines documented with an object directive are inserted after a
   ``.. f:currentmodule::`` line, so they are registered **without a
   module** (as ``_/name``). References by short name, such as
   ``:f:func:`linspace```, resolve as usual.


``.. f:autotype::``
-------------------

Document a Fortran derived type, with its components.

.. code-block:: rst

   .. f:autotype:: point

The directive has **no option**. The type description and the components,
rendered as ``:f`` fields, are those of the source (see
:doc:`how_to_comment`, *Derived Types*). Type-bound procedures are not
documented.


``.. f:autovariable::``
-----------------------

Document a Fortran module variable.

.. code-block:: rst

   .. f:autovariable:: beta

The directive has **no option**. It writes the ``f:variable`` directive with
the options ``:type:``, ``:shape:`` and ``:attrs:`` deduced from the
declaration and the description of the source. A real example from
``ED_INPUT_VARS``, ``.. f:autovariable:: nbath``:

.. code-block:: rst

   .. f:variable:: nbath

      Number of bath sites:

       * :f:var:`bath_type` = :code:`normal` : number of bath sites per orbital

       * :f:var:`bath_type` = :code:`hybrid` : total number of bath sites

       * :f:var:`bath_type` = :code:`replica/general` : number of replicas

      :Type: integer

      :Bindings: Language = **c**, Name = **nbath**
      :Default: 6


``.. f:autoprogram::``
----------------------

Document a main ``program`` unit.

.. code-block:: rst

   .. f:autoprogram:: main

The description block under the ``program`` line is used as for a routine,
and the ``use`` statements are listed in a ``:use:`` field.


``.. f:autosrcfile::``
----------------------

Document all the objects defined in one source file: the program, the module
and the stand-alone functions and subroutines, in that order.

.. code-block:: rst

   .. f:autosrcfile:: solver.f90
      :objtype: module
      :search_mode: strict

Options
~~~~~~~

``:objtype:``
   Restrict to one of ``program``, ``module``, ``function`` or
   ``subroutine``. Only one value is understood.

``:search_mode:``
   With ``strict``, the argument has to be the full path of the file as it
   was found by ``fortran_src``. Otherwise (default) only the base name of
   the file is compared.

.. warning::

   The argument is converted to lower case and then compared, with the
   case preserved, to the file name. A file whose name contains capitals, such
   as ``SF_ARRAYS.f90``, is therefore never found and the warning
   ``No valid content found for file`` is emitted. Files with a lower-case
   name work, and so does ``:search_mode: strict`` with a fully lower-case
   absolute path. Use ``f:automodule`` when in doubt.


Documentation Comments
----------------------

Documentation is extracted from comments **inside** the documented entity
(after its opening statement) and from the comment at the end of each
declaration. See :doc:`how_to_comment` for the complete rules.

.. code-block:: fortran

   subroutine solve(A, b, x)
   !Solve a linear system Ax = b using LU factorization without pivoting.
     real, intent(in)  :: A(:,:) !Coefficient matrix
     real, intent(in)  :: b(:)   !Right-hand side
     real, intent(out) :: x(:)   !Solution
   end subroutine solve

Comments written before the ``subroutine`` line, and Doxygen markers
(``!>``, ``!!``), are not interpreted.


Automatic contents
------------------

The following information is deduced from the code and needs no comment:

* the **signature**, with the optional arguments in square brackets;
* the **type**, the **shape** and the **attributes** of each argument, of the
  result of a function, of each module variable and of each component of a
  type; the ``intent`` is displayed, in brackets, in front of the other
  attributes;
* the **default value** of a variable initialised in its declaration;
* the **C bindings**: ``bind(c, name="x")`` on a variable or on a routine
  is displayed in a ``:Bindings:`` field;
* the ``use`` statements, in ``Used modules`` (modules of the project),
  ``External modules`` (others) or in a ``:use:`` field for routines,
  including the ``only`` lists and ``local => remote`` renamings, which are
  displayed in the same direction, as ``local ⇒ remote``;
* the arguments of a **generic interface**, merged from all its
  ``module procedure`` implementations.


Cross-Referencing
-----------------

Documented entities can be referenced using Fortran-domain roles, in the
``.rst`` files as well as in the Fortran comments:

.. code-block:: rst

   :f:mod:`linalg`
   :f:func:`linalg/solve`
   :f:type:`matrix`
   :f:var:`beta`

The text generated by the autodoc directives already contains such links: the
quick access lists, the ``use`` lists and the routine aliases. The roles are
detailed in :ref:`domain-roles`. If a name is not defined in the project but
is found in an Intersphinx inventory that contains Fortran objects, the link
is made to that inventory.



Notes and Limitations
---------------------

- A generic interface is documented as one entry; its specific procedures
  are documented separately when they are public
- Preprocessor conditionals are not evaluated
- Accurate documentation depends on correct parsing of the Fortran source
- Names must be given in lower case
- Fortran files are not registered as dependencies of the pages (see
  :doc:`quickstart`)

Further behaviours that may surprise, with workarounds, are collected in
:doc:`limitations`. For edge cases, manual use of the Fortran domain
directives may provide greater control.
