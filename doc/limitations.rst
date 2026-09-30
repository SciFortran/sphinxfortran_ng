Known limitations
=================

This page collects the behaviours of the current version that differ from
what one may expect. Each was reproduced on small test sources. When a
workaround exists it is given.

.. contents:: On this page
   :local:
   :depth: 1


Comments
--------

Comments before the entity are ignored, and ``!>`` / ``!!`` are not markers
   The description is read from the lines *after* the opening statement.
   Doxygen-style markers are copied verbatim (``!> text`` gives
   ``> text``). See :doc:`how_to_comment`.

A ``use`` or ``implicit none`` before the description hides it
   The comment must be the first thing after the signature.

``$1``, ``$2`` positional descriptions do not work
   The parser has support for lines such as ``$2: description`` in the header
   comment of a routine, but the pattern does not match a line beginning with
   ``$``. Use the name of the argument.

A header line beginning with an argument name is taken as its description
   ``x is scaled in place`` sets the description of ``x`` and stays in the
   text. Start sentences with another word.

Variable descriptions are single-line
   The continuation lines of a variable are joined without any separator (add
   a trailing space), a bare ``!`` ends the description, and a variable
   cannot hold a literal block or several paragraphs. Only the first
   ``:Label var:`value``` line of a variable is kept.

Doubled ``:Default:``
   A variable with an initialiser *and* a ``:Default var:`...``` line in its
   comment shows two ``:Default:`` fields. Keep one.


Declarations
------------

Derived types
   ``type :: name``, ``type, public :: name`` and ``type, extends(...) ::
   name`` are listed without description and without component descriptions.
   Use ``type name``. In a module made private by a ``private`` statement, the
   ``public :: name`` statement of a type must **follow** the definition.
   Type-bound procedures are not documented.

Kinds are not shown
   ``real(8)``, ``real(kind=dp)`` and ``real(c_double)`` are all displayed as
   ``real`` (``character`` lengths are kept).

Optional flag of dimension arguments
   An argument used only to dimension an optional array may be reported as
   optional (see :doc:`examples`).

Preprocessing
   ``#ifdef`` and ``#if`` are not evaluated. The code of every branch is
   read: the modules used in several branches are all listed (this is why
   ``mpi`` and ``sf_mpi`` both appear for ``ed_read_input``).

Order
   Module variables are listed alphabetically (and the variables of derived
   types in declaration order); routines follow the order of the source in
   the module.

Case
   All names are lower-cased by the parser. Use lower-case names in the
   directives (``f:automodule:: sf_arrays``) and roles.


Directives and options
----------------------

``:include-private:`` does nothing
   Use ``:forceadd-members:`` (names of private members to document) or
   ``:members:``.

``:undoc-members:`` excludes
   It is the *list of members to hide*, the reverse of the Python autodoc
   option of the same name. Undocumented members are always displayed. It
   overrides ``:members:``.

``:hide-output:`` needs a value
   Write ``:hide-output: 1``. A bare option is ignored.

``:subsection_type:`` accepts ``rubric`` and ``title`` only
   The value ``section`` is treated as ``rubric``.

``:indent:``
   Only ``tab`` and ``space``. Set the width once with ``fortran_indent``.

``f:autointerface``
   Currently returns the argument list only, not the full description. Use
   ``f:autoroutine`` with the name of the interface: it produces the
   ``f:interface`` block with the arguments merged from the specific
   procedures.

``f:autosrcfile`` and capital letters
   The name is lower-cased before it is compared with the base name of the
   file: files with capitals in their name (``SF_ARRAYS.f90``) are never
   found. Use ``f:automodule``.

``f:autosrcfile :objtype:``
   Takes a single value.

Object directives take no options
   ``f:autoroutine``, ``f:autotype``, ``f:autovariable``, ``f:autoprogram``
   and the other object directives do not accept ``:noindex:`` or any other
   option.

Unknown object names
   The warning ``Wrong routine name: ...`` is followed by a Python
   ``KeyError`` that stops the directive. Check the name (and its case).

Configuration values that are not read
   ``fortran_encoding`` and ``fortran_subsection_type`` are declared but
   currently ignored.


Domain
------

Signatures with ``result(...)`` or a leading type are not parsed
   ``.. f:function:: f(x) result(y)`` and ``.. f:function:: real function f(x)``
   are displayed as raw text; the object has no index entry and cannot be
   referenced. Write ``f(x)`` and describe the result in a ``:r`` field.

``:r`` needs a name
   ``:returns: text`` without a name raises an ``IndexError``. Write
   ``:r real y: text``.

Types and attributes containing spaces
   In a ``:p`` field, ``real, dimension(:,:) A`` and
   ``x [intent(in), optional]`` are mis-analysed. Use ``:type A: ...`` or
   attributes without inner parentheses or spaces.

``f:currentmodule``
   The argument is ignored and the current module is always reset to nothing.
   After an ``f:auto*`` object directive, the objects that follow are
   therefore not linked to a module.

``f:module`` has no content
   Text has to follow, not be indented under the directive.

Ambiguous names
   A message ``more than one target found`` is printed and the first match is
   used. Use ``module/name`` or ``preferred-crossrefs``.

Incremental builds
   Fortran files are not dependencies of the pages that document them; use
   ``sphinx-build -E`` or touch the ``.rst`` file after editing a source.

Unresolved names in comments
   A role in a Fortran comment that points to something not documented in the
   project (for example ``:f:func:`parse_input_variable``` in
   ``ED_INPUT_VARS``, which belongs to SciFortran) is simply displayed
   as text, without a link. It only warns when ``nitpicky = True``.
