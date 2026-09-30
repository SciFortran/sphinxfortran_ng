Examples
========

This page walks through two real modules of the SciFortran / EDIpack code
base. They were chosen because they sit at the two ends of what a Fortran
documentation tool has to cope with:

``SF_ARRAYS``
   A **library of functions**. The documentation is in the routines:
   descriptions, arguments, optional arguments, results.

``ED_INPUT_VARS``
   A module made of **about 120 input variables** and a handful of routines,
   with C bindings, default values, lists of allowed values, LaTeX and
   preprocessor directives.

The sources are copied in the ``examples`` folder of the documentation, which
is the ``fortran_src`` directory of ``conf.py``. Each example ends with its
*live rendering*, built by the directives shown there. Every block of
reStructuredText in between is the actual output of the parser.

.. contents:: On this page
   :local:
   :depth: 2


Example 1: a library of functions (``SF_ARRAYS``)
-------------------------------------------------

The module begins with a one-line description, right under the ``module``
statement, followed by its ``public`` statements:

.. code-block:: fortran

   module SF_ARRAYS
   !SciFortran module for array creation and manipulation
     implicit none

     !GRIDS:
     public :: linspace
     public :: logspace
     ...
   contains

Two-line documentation in the ``.rst`` file is all that is needed:

.. code-block:: rst

   .. f:automodule:: sf_arrays

The head of the generated text (the one-line description is used as
synopsis in the module index, and *Quick access* lists the public routines):

.. code-block:: rst

   .. f:module:: sf_arrays
      :synopsis: SciFortran module for array creation and manipulation

   .. rubric:: Description

   SciFortran module for array creation and manipulation

   .. rubric:: Quick access

   :Routines: :f:func:`arange`, :f:func:`linspace`, :f:func:`logspace`, :f:func:`powspace`, :f:func:`upminterval`, :f:func:`upmspace`

A function with optional arguments: ``linspace``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: fortran

   function linspace(start,stop,num,istart,iend,mesh) result(array)
   !
   !Returns an array of evenly spaced numbers over a specified interval.
   !Returns :f:var:`num` evenly spaced samples, calculated over the interval [:f:var:`start`, :f:var:`stop`].
   !The start and end points of the interval can optionally be excluded.
   !
     real(8)          :: start           !Starting value of the sequence
     real(8)          :: stop            !End value of the sequence
     integer          :: num             !Number of samples to generate
     logical,optional :: istart          !If :code:`.true.`, :f:var:`start` is included in the resulting array. Default :code:`.true.`
     logical,optional :: iend            !If :code:`.true.`, :f:var:`stop` is included in the resulting array. Default :code:`.true.`
     real(8),optional :: mesh            !If present, the step is saved in this variable
     real(8)          :: array(num)      !Contains :f:var:`num` equally spaced samples in the interval
                                         ![:f:var:`start`, :f:var:`stop`], left/right open or closed depending on
                                         !:f:var:`istart` and :f:var:`iend`

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

What the parser did for us:

* ``optional`` in the declarations gave the brackets in the signature and the
  ``:o`` fields;
* ``result(array)`` selected the variable that is documented in the ``:r``
  field, with its shape ``(num)``;
* ``real(8)`` is shown as ``real``: the kind is not part of the output;
* the three comment lines of ``array`` were joined into one description
  (each line ends with a space).

Mathematics and cross-references: ``upmspace``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Descriptions are reStructuredText, so LaTeX maths and links are available:

.. code-block:: fortran

   function upmspace(start,stop,p,u,ndim,base,istart,iend,mesh) result(aout)
   !
   !Returns an array of number spaced linearly between exponentially spaced checkpoints.
   !The interval [:f:var:`start`, :f:var:`stop`] is first divided into :f:var:`p`
   !coarse regions, the width of which is exponentially increasing so that the
   !i-th checkpoint is (:f:var:`stop` - :f:var:`start`) :math:`\cdot` :f:var:`base` ^ ( - :f:var:`p` + :code:`i` ).
   !Each of the coarse intervals is then linearly divided in :f:var:`u` subintervals.
   !
     real(8)          :: start  !First element of the array
     ...
     integer          :: ndim   !Length of the out array, must be :math:`p \cdot u` or  :math:`p \cdot u + 1`
     real(8),optional :: mesh(ndim) !If present, contains the distances between consecutive points in :f:var:`aout`.
                                    !The last element is :code:`aout(ndim) - aout(ndim-1)`

.. code-block:: rst

   .. f:function:: upmspace(start, stop, p, u, ndim[, base, istart, iend, mesh])

      Returns an array of number spaced linearly between exponentially spaced checkpoints.
      The interval [:f:var:`start`, :f:var:`stop`] is first divided into :f:var:`p`
      coarse regions, the width of which is exponentially increasing so that the
      i-th checkpoint is (:f:var:`stop` - :f:var:`start`) :math:`\cdot` :f:var:`base` ^ ( - :f:var:`p` + :code:`i` ).
      Each of the coarse intervals is then linearly divided in :f:var:`u` subintervals.

      :p real start: First element of the array
      :p real stop: Last element of the array
      :p integer p: Number of coarse subdivisions
      :p integer u: Number of fine subdivisions
      :o integer ndim: Length of the out array, must be :math:`p \cdot u` or  :math:`p \cdot u + 1`
      :o real base: Base of the exponential spacing (default :code:`2`)
      :o logical istart: If :code:`.true.`, :f:var:`start` is included in the resulting array. Default :code:`.true.`
      :o logical iend: If :code:`.true.`, :f:var:`stop` is included in the resulting array. Default :code:`.true.`
      :o real mesh(ndim): If present, contains the distances between consecutive points in :f:var:`aout`. The last element is :code:`aout(ndim) - aout(ndim-1)`
      :r real aout(ndim): Contains :f:var:`p` coarse exponentially-spaced checkpoints, each two of which separated by :f:var:`u` linearly spaced points

.. note::

   ``ndim`` is declared plainly (``integer :: ndim``) yet is shown with the
   ``:o`` field, although the signature does not bracket it. This comes from
   the f2py-derived parser, which treats an argument that is only used to
   dimension another one (here ``mesh(ndim)``, an optional array) as
   optional with an inferred value. Compare the generated fields with the
   declarations, which are the reference. To get a plain ``:p`` field, the
   ``:o`` / ``:p`` role cannot be changed from the comment: write the routine
   by hand with ``f:function`` if it matters.

Cross-references to a routine
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``upminterval`` refers to ``upmspace`` with a role written **in the Fortran
comment**:

.. code-block:: fortran

   !This is achieved by calling :f:func:`upmspace` twice in a mirror-like fashion.

In the built page this is a link to the description of ``upmspace``.

Documenting one routine only
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: rst

   .. f:autoroutine:: powspace

If a routine needs a handwritten paragraph, ``f:automodule`` can declare the
module while the routines are placed where you want them:

.. code-block:: rst

   .. f:automodule:: sf_arrays
      :hide-output: 1

   Linear grids
   ------------

   .. f:autoroutine:: linspace
   .. f:autoroutine:: arange

   Exponential grids
   -----------------

   .. f:autoroutine:: powspace
   .. f:autoroutine:: upmspace


Live rendering of ``SF_ARRAYS``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Everything below is generated from ``examples/SF_ARRAYS.f90`` by

.. code-block:: rst

   .. f:automodule:: sf_arrays

.. f:automodule:: sf_arrays


Example 2: a module of input variables (``ED_INPUT_VARS``)
----------------------------------------------------------

This module has few routines and many variables, described in the
*trailing-bang style* (see :doc:`how_to_comment`): the declaration ends with
a bare ``!`` and the description follows on the next comment lines, a bare
``!`` closing it.

.. code-block:: fortran

   MODULE ED_INPUT_VARS
     !:synopsis: User-accessible input variables
     !Contains all global input variables which can be set by the user through the input file.
     ...
     USE SF_VERSION
     USE SF_PARSE_INPUT
     USE SF_IOTOOLS, only:str,free_unit,to_upper,to_lower
     USE ED_VERSION
     use iso_c_binding
     implicit none

The generated head (the *Quick access* list has 119 variables and is shortened
here):

.. code-block:: rst

   .. f:module:: ed_input_vars
      :synopsis: User-accessible input variables

   .. rubric:: Description

   Contains all global input variables which can be set by the user through the input file. A specific preocedure :f:func:`ed_read_input` should be called to read the input file using :f:func:`parse_input_variable` procedure from SciFortran. All variables are automatically set to a default, looked for and updated by reading into the file and, sequentially looked for and updated from command line (std.input) using the notation `variable_name=variable_value(s)` (case independent).

   .. rubric:: Quick access

   :Variables: :f:var:`a_ph`, :f:var:`bath_type`, :f:var:`beta`, ... (119 entries)
   :Routines: :f:func:`ed_read_input`, :f:func:`ed_update_input`, :f:func:`print_logo`, :f:func:`s_chop`, :f:func:`substring_delete`

   .. rubric:: External modules

   - :f:mod:`sf_version`

   - :f:mod:`sf_parse_input`

   - :f:mod:`sf_iotools`

      - :f:func:`~sf_iotools/str`
      -  :f:func:`~sf_iotools/free_unit`
      -  :f:func:`~sf_iotools/to_upper`
      -  :f:func:`~sf_iotools/to_lower`

   - :f:mod:`ed_version`

   - :f:mod:`iso_c_binding`

A variable with a list of allowed values and a default
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: fortran

   integer(c_int),bind(c, name="Nbath")   :: Nbath   !
   !Number of bath sites:
   ! * :f:var:`bath_type` = :code:`normal` : number of bath sites per orbital
   ! * :f:var:`bath_type` = :code:`hybrid` : total number of bath sites
   ! * :f:var:`bath_type` = :code:`replica/general` : number of replicas
   ! :Default Nbath:`6`
   !

.. code-block:: rst

   .. f:variable:: nbath

      Number of bath sites:

       * :f:var:`bath_type` = :code:`normal` : number of bath sites per orbital

       * :f:var:`bath_type` = :code:`hybrid` : total number of bath sites

       * :f:var:`bath_type` = :code:`replica/general` : number of replicas

      :Type: integer

      :Bindings: Language = **c**, Name = **nbath**
      :Default: 6

* ``* item`` lines became a bullet list;
* ``:Default Nbath:`6``` was removed from the text and became the
  ``:Default:`` field;
* ``bind(c, name="Nbath")`` became the ``:Bindings:`` field, and ``integer(c_int)``
  the type ``integer``.

An array variable
~~~~~~~~~~~~~~~~~

.. code-block:: fortran

   real(c_double),dimension(5),bind(c, name="Uloc")   :: Uloc   !
   !Values of the local interaction per orbital (max :code:`5` )
   ! :Default Uloc:`(/( 2d0,i=1,Norb )/)`
   !

.. code-block:: rst

   .. f:variable:: uloc

      Values of the local interaction per orbital (max :code:`5` )

      :Type: real(5)

      :Bindings: Language = **c**, Name = **uloc**
      :Default: (/( 2d0,i=1,Norb )/)

The shape is appended to the type: ``real(5)`` is a real array with five
elements.

Mathematics, and a warning in a variable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: fortran

   character(len=12)    :: cg_norm   !
   !Which norm to use in the evaluation of the :math:`\chi^{2}` for matrix quantities.
   ! * :code:`ELEMENTAL` : :math:`\chi^{2}` is the sum of each component's :math:`\chi^{2}`
   ! * :code:`FROBENIUS` : :math:`\chi^{2}` is calculated on the Frobenius norm (Matrix distance)
   ! :Default cg_norm:`ELEMENTAL`
   !.. warning::
   !   The Frobenius norm is currently implemented only for ...

.. code-block:: rst

   .. f:variable:: cg_norm

      Which norm to use in the evaluation of the :math:`\chi^{2}` for matrix quantities.

       * :code:`ELEMENTAL` : :math:`\chi^{2}` is the sum of each component's :math:`\chi^{2}`

       * :code:`FROBENIUS` : :math:`\chi^{2}` is calculated on the Frobenius norm (Matrix distance)

       .. warning::    The Frobenius norm is currently implemented only for :f:var:`ed_bath` = :code:`replica, general`.    Also, for :f:var:`cg_pow` :math:`\neq 2`  the Frobenius norm is ill-defined, at least with respect    to its usual mathematical meaning. The behavior of :code:`cg_norm=frobenius` might be changed or    removed in future versions of the code, breaking back-compatibility.

      :Type: character(len=12)

      :Default: ELEMENTAL

The admonition is written as a single line by the parser: its content
follows the ``.. warning::`` marker on the same line, which docutils reads as
the content of the warning. It is placed **after** the ``:Default:`` field in
the source, but the field is displayed at the end of the description.

Logical flags and text following the list
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When text follows a list, the list is closed automatically by the blank lines
that the parser inserts:

.. code-block:: rst

   .. f:variable:: ed_total_ud

      Flag to select which type of quantum numbers have to be considered (if :f:var:`ed_mode` = :code:`normal`)

       * :code:`T` : blocks have different total :math:`N_{\uparrow}` and :math:`N_{\downarrow}`

       * :code:`F` : blocks have different total :math:`N^{\alpha}_{\uparrow}` and :math:`N^{\alpha}_{\downarrow}`

      where :math:`\alpha` is the orbital index. Speeds up calculation in the case where orbitals are not hybridized

      :Type: logical

      :Bindings: Language = **c**, Name = **ed_total_ud**
      :Default: T

Variables with a ``save`` attribute
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``LOGfile`` is declared ``integer(c_int),bind(c, name="LOGfile"),save``. The
non-``bind`` attributes go into the ``:Attributes:`` field:

.. code-block:: rst

   .. f:variable:: logfile

      Logfile unit

      :Type: integer

      :Attributes: save
      :Bindings: Language = **c**, Name = **logfile**
      :Default: 6

Routines of the module
~~~~~~~~~~~~~~~~~~~~~~

``ed_read_input`` is documented by one description line under its signature:

.. code-block:: fortran

   subroutine ed_read_input(INPUTunit)
     !
     !This functions reads the input file provided by :code:`INPUTunit` and sets the global variables accordingly
   #ifdef _MPI
     USE MPI
     USE SF_MPI
   #endif
     character(len=*) :: INPUTunit

.. code-block:: rst

   .. f:subroutine:: ed_read_input(inputunit)

      This functions reads the input file provided by :code:`INPUTunit` and sets the global variables accordingly

      :p character(len=*) inputunit:
      :use: :f:mod:`mpi`, :f:mod:`sf_mpi`

Note the ``:use:`` field: both ``mpi`` and ``sf_mpi`` are listed because the
preprocessor is not run. ``INPUTunit`` has no description, so the field is
empty; add a comment at the end of its declaration to fill it.

Which variables need attention?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Running the parser on the module shows 119 module variables, of which 105
have a description. Of the 14 remaining ones:

* 11 are the internal helpers ending in ``_`` (``ed_twin_``, ``uloc_``,
  ``pair_field_``, ...): they have no description because they are
  implementation details of the input reader. They are listed in the
  documentation because they are public. Exclude them with
  ``:undoc-members:`` (see the live rendering below), or declare them ``private``;
* ``g_ph_diag`` and ``niter`` really lack a description: ``g_ph_diag`` has
  the description on the next lines but no trailing ``!`` on the declaration,
  and ``niter`` has a bare ``!`` followed by a blank;
* ``normal_complex`` is set by the preprocessor and has no comment.

Two things in the source of ``cg_norm`` are worth fixing by the author:
the warning refers to ``:f:var:`ed_bath```, which does not exist (the
variable is ``bath_type``), so the link stays unresolved, and the module
description says "preocedure".


Live rendering of ``ED_INPUT_VARS``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Everything below is generated from ``examples/ED_INPUT_VARS.f90``. The
variables whose name ends in an underscore are internal helpers of the input
reader and are left out with ``:undoc-members:``:

.. code-block:: rst

   .. f:automodule:: ed_input_vars
      :undoc-members: chidens_flag_, chiexct_flag_, chipair_flag_, chispin_flag_,
                      ed_read_umatrix_, ed_total_ud_, ed_twin_, ed_use_kanamori_,
                      pair_field_, rdm_flag_, uloc_

.. f:automodule:: ed_input_vars
   :undoc-members: chidens_flag_, chiexct_flag_, chipair_flag_, chispin_flag_, ed_read_umatrix_, ed_total_ud_, ed_twin_, ed_use_kanamori_, pair_field_, rdm_flag_, uloc_
