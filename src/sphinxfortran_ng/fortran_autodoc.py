# -*- coding: utf-8 -*-
"""Sphinx extension for autodocumenting Fortran codes.

Sources are parsed with :mod:`.crackfortran_for_sphinx`, enriched with the
comments found in the code by :class:`F90toRst`, and converted to reStructuredText
that is interpreted by the directives of :class:`.fortran_domain.FortranDomain`.
"""
# Copyright or © or Copr. Actimar/IFREMER (2010-2019)
#
# This software is a computer program whose purpose is to provide
# utilities for handling oceanographic and atmospheric data,
# with the ultimate goal of validating the MARS model from IFREMER.
#
# This software is governed by the CeCILL license under French law and
# abiding by the rules of distribution of free software.  You can  use,
# modify and/ or redistribute the software under the terms of the CeCILL
# license as circulated by CEA, CNRS and INRIA at the following URL
# "http://www.cecill.info".
#
# As a counterpart to the access to the source code and  rights to copy,
# modify and redistribute granted by the license, users are provided only
# with a limited warranty  and the software's author,  the holder of the
# economic rights,  and the successive licensors  have only  limited
# liability.
#
# In this respect, the user's attention is drawn to the risks associated
# with loading,  using,  modifying and/or developing or reproducing the
# software by the user in light of its specific status of free software,
# that may mean  that it is complicated to manipulate,  and  that  also
# therefore means  that it is reserved for developers  and  experienced
# professionals having in-depth computer knowledge. Users are therefore
# encouraged to load and test the software's suitability as regards their
# requirements in conditions enabling the security of their systems and/or
# data to be ensured and,  more generally, to use and operate it in the
# same conditions as regards security.
#
# The fact that you are presently reading this means that you have had
# knowledge of the CeCILL license and that you accept its terms.
#
import os
import re
from collections import OrderedDict
from glob import glob
from operator import itemgetter

from docutils.parsers.rst import Directive
from docutils.parsers.rst.directives import unchanged
from docutils.statemachine import string2lines
from sphinx.util import logging
from sphinx.util.console import bold

from . import crackfortran_for_sphinx as cracker
from .crackfortran_for_sphinx import crackfortran, fortrantypes
from sphinxfortran_ng.fortran_domain import FortranDomain, f_sep

logger = logging.getLogger(__name__)

#: Object names found in the intersphinx inventories, by object type
fortran_invs = {}
#: Last non empty description found for each block name
backup_desc = {}

_CALLABLES = ('function', 'subroutine', 'program', 'interface')
_DESCRIBED = ('function', 'subroutine', 'type')
_BIND_RE = re.compile(r'bind\(\s*(\w+)\s*,\s*name\s*=\s*"(\w+)"\s*\)')


class F90toRstException(Exception):
    """Error raised when an unknown Fortran object is requested."""


def _finder(names, fmt):
    """Get a ``findall`` function for ``fmt % 'name1|name2|...'``.

    It returns an empty list when *names* is empty."""
    if not names:
        return lambda line: []
    return re.compile(fmt % '|'.join(names), re.I).findall


class F90toRst(object):
    '''Fortran 90 parser and restructeredtext formatter

    :Parameters:

         - **ffiles**: Fortran files (glob expression allowed) or dir (or list of)

    :Options:

        - **ic**: Indentation char.
        - **ulc**: Underline char for titles.
        - **sst**: Subsection type, ``"title"`` or ``"rubric"``.
        - **vl**: Verbose level (0=quiet).
        - **encoding**: Kept for compatibility, files are read with the default encoding.

    The following attributes can be changed at any time (the auto directives do it
    through their options): ``ic``, ``ulc``, ``sst``, ``members``, ``undoc_members``,
    ``forceadd_members`` (comma separated names), ``hide_output`` and ``exclude_private``.
    '''
    _re_unended_match = re.compile(r'(.*)&\s*', re.I).match
    _re_unstarted_match = re.compile(r'\s*&(.*)', re.I).match
    _re_comment_match = re.compile(r'\s*!(.*)', re.I).match
    _re_space_prefix_match = re.compile(r'^(\s*).*$', re.I).match
    _fmt_vardesc = ':%(role)s %(vtype)s %(vname)s%(vdim)s%(vattr)s: %(vdesc)s'

    def __init__(self, ffiles, ic='\t', ulc='-', vl=0, encoding='utf8', sst='rubric'):
        if not isinstance(ffiles, list):
            ffiles = [ffiles]
        self.ffiles = ffiles
        self.ic = ic
        self.ulc = ulc
        self.sst = sst
        self.members = []
        self.undoc_members = []
        self.forceadd_members = []
        self.hide_output = False
        self.exclude_private = True

        # Read sources (last character of each line is dropped)
        self.src = OrderedDict()
        for ff in ffiles:
            with open(ff) as f:
                self.src[ff] = [line[:-1] for line in f.readlines()]

        # Crack files
        cracker.verbose = vl
        cracker.quiet = 1 - vl
        self.crack = []
        for ff in ffiles:
            self.crack.extend(crackfortran(ff))

        self.build_index()
        self.scan()
        self.build_callfrom_index()

    # Indexing ---

    def build_index(self):
        """Register modules, routines, types and variables for quick access

        Index constituents are dictionaries of cracked blocks, named
        :attr:`modules`, :attr:`types`, :attr:`variables`, :attr:`programs` and
        :attr:`routines`. The latter is also available as :attr:`functions`,
        :attr:`subroutines` and :attr:`interfaces` (same object).
        """
        self.modules = OrderedDict()
        self.types = OrderedDict()
        self.routines = self.interfaces = self.functions = self.subroutines = OrderedDict()
        self.variables = OrderedDict()
        self.programs = OrderedDict()

        for block in self.crack:

            if block['block'] == 'module':
                module = block['name']
                self.modules[module] = block

                # Types and routines
                for sub in block['body']:
                    if sub['block'] in ('function', 'type', 'subroutine', 'interface'):
                        getattr(self, sub['block'] + 's')[sub['name']] = sub
                        sub['module'] = module
                        if sub['name'] in block['vars']:
                            sub['attrspec'] = block['vars'][sub['name']].get('attrspec', [])
                        for varname in sub['sortvars']:
                            sub['vars'][varname]['name'] = varname

                # Function aliases from "use only" (rescan)
                for bfunc in list(self.routines.values()):
                    bfunc['aliases'] = []
                if any(sub['block'] == 'use' for sub in block['body']):
                    for monly in list(block['use'].values()):
                        if not monly:
                            continue
                        for fname, falias in list(monly['map'].items()):
                            self.routines[falias] = self.routines[fname]
                            if falias not in self.routines[fname]['aliases']:
                                self.routines[fname]['aliases'].append(falias)

                # Module variables
                for varname in sorted(block['sortvars']):
                    if varname not in self.routines and varname not in self.types:
                        bvar = block['vars'][varname]
                        self.variables[varname] = bvar
                        bvar['name'] = varname
                        bvar['module'] = module

            # Local functions, subroutines and programs
            elif block['block'] in ('function', 'subroutine', 'program'):
                getattr(self, block['block'] + 's')[block['name']] = block
                for varname in block['sortvars']:
                    block['vars'][varname]['name'] = varname

        # Regular expressions for fast search of calls
        routines = list(self.routines.values())
        self._re_callsub_findall = _finder(
            [re.escape(b['name'].lower()) for b in routines
             if b['block'] in ('subroutine', 'interface')], r'call\s+\b(%s)\b')
        self._re_callfunc_findall = _finder(
            [re.escape(b['name'].lower()) for b in routines
             if b['block'] == 'function'], r'\b(%s)\b\s*\(')

        # Regular expressions for variable descriptions
        # - in the header comment of routines and types
        for block in routines + list(self.types.values()):
            names = '|'.join(block['sortvars']) + r'|\$(?P<varnum>\d+)'
            block['vardescmatch'] = re.compile(
                r'[\s\*\-:]*(?:@param\w*)?\b(?P<varname>%s)\b\W+(?P<vardesc>.*)' % names).match
        # - in inline comments (reversed+sorted avoids conflicts between variables sharing a prefix)
        for block in list(self.types.values()) + list(self.modules.values()) + routines:
            if block['sortvars']:
                names = '|'.join(reversed(sorted(map(re.escape, block['sortvars']))))
                block['vardescsearch'] = re.compile(
                    r'.*\b(?P<varname>%s)(?!\s*\()[^\)]*\b(?!\s*\()[^\w]*\s*(?P<dims>\([^\)]*\))?[^!\)]*!\s*(?P<vardesc>.*)\s*' % names,
                    re.I).search
                block['vardescsearch_fallback'] = re.compile(
                    r'.*\b(?P<varname>%s)\b\s*(?P<dims>\([^\)]*\))?[^!\)]*!\s*(?P<vardesc>.*)\s*' % names,
                    re.I).search
            else:
                block['vardescsearch'] = block['vardescsearch_fallback'] = lambda x: None

    def build_callfrom_index(self):
        """Register in each routine ``callfrom``, the names of the routines and programs calling it"""
        callers = list(self.routines.values()) + list(self.programs.values())
        for bfunc in list(self.routines.values()):
            bfunc['callfrom'] = [b['name'] for b in callers if bfunc['name'] in b['callto']]

    def filter_by_srcfile(self, sfile, mode=None, objtype=None, **kwargs):
        """Search for blocks according to origin file

        :Params:
            - **sfile**: Source file name.
            - **mode**, optional: If ``"strict"``, exact match is needed, else only basename.
            - **objtype**, optional: Restrict search to one or a list of block types
              (i.e. ``"function"``, ``"program"``, etc).
        """
        strict = mode == 'strict'
        if objtype and not isinstance(objtype, list):
            objtype = [objtype]
        if not strict:
            sfile = os.path.basename(sfile)
        bb = []
        for b in self.crack:
            if objtype and b['block'] not in objtype:
                continue
            bfile = b['from'].split(':')[0]  # remove module name
            if not strict:
                bfile = os.path.basename(bfile)
            if sfile == bfile:
                bb.append(b)
        return bb

    # Scanning ---

    def scan(self):
        """Read descriptions (comments) of all modules, routines, types and variables"""
        for block in self.crack:

            if block['block'] == 'module':
                modsrc = self.get_blocksrc(block)
                block['desc'], block['synopsis'] = self.get_comment(modsrc, aslist=True)
                for sub in block['body']:
                    self.scan_container(sub, insrc=modsrc)

                # Module variables
                self.strip_blocksrc(block, ['type', 'function', 'subroutine', 'interface'], src=modsrc)
                if modsrc and 'vardescsearch' in block:
                    self._scan_inline_desc(block, modsrc, 'vardescsearch')
                for bvar in list(block['vars'].values()):
                    bvar.setdefault('desc', '')

            elif block['block'] in ('function', 'subroutine', 'program'):
                self.scan_container(block)

    def _scan_inline_desc(self, block, src, key, var_done=None):
        """Get variable descriptions from inline ``!`` comments of *src*

        :Params:
            - **key**: Name of the regular expression of *block* used to find variables.
            - **var_done**, optional: List of variables to skip, that is updated in place.
        """
        search = block.get(key)
        if search is None:
            return
        nameold = None
        for line in src:
            stripped = line.strip()
            if stripped.startswith('!') and stripped != '!':
                # Continuation of the description of the last variable
                if nameold is not None:
                    text = line.lstrip()[1:]
                    sep = '\n\n' if text.lstrip().startswith('*') else ''
                    block['vars'][nameold]['desc'] += sep + text + sep
                continue
            nameold = None
            m = search(line)
            if m and (var_done is None or m.group('varname') not in var_done):
                nameold = m.group('varname').lower()
                block['vars'][nameold]['desc'] = m.group('vardesc')
                if var_done is not None:
                    var_done.append(m.group('varname'))

    def scan_container(self, block, insrc=None):
        """Scan a block of program, routine or type: description, variables and calls"""
        if block['block'] not in ('type', 'function', 'subroutine', 'program', 'interface'):
            return
        subsrc = self.get_blocksrc(block, insrc)

        # Comment
        block['desc'], block['synopsis'] = self.get_comment(subsrc, aslist=True)
        if block['desc'] and block['name'] not in backup_desc:
            backup_desc[block['name']] = block['desc']

        # Variable descriptions in the header comment
        if block['desc'] and block['block'] in _DESCRIBED and 'vardescmatch' in block:
            for iline, line in enumerate(block['desc']):
                m = block['vardescmatch'](line)
                if not m:
                    continue
                varname = m.group('varname')
                if m.group('varnum'):  # $[1-9]+
                    ivar = int(m.group('varnum')) - 1
                    if ivar < 0 or ivar >= len(block['args']):
                        continue
                    varname = block['args'][ivar]
                    block['desc'][iline] = line.replace(m.group('varname'), varname)
                if varname != '':
                    block['vars'][varname]['desc'] = m.group('vardesc')

        # Index calls
        if block['block'] in _CALLABLES:
            block['callto'] = []
            if subsrc is not None:
                self.join_src(subsrc)
                for line in subsrc[1:-1]:
                    if line.strip().startswith('!'):
                        continue
                    line = line.lower()
                    for fn in self._re_callsub_findall(line) + self._re_callfunc_findall(line):
                        if fn not in block['callto']:
                            block['callto'].append(fn)

        # Inline descriptions overwrite those of the header comment
        if block['block'] in _DESCRIBED and subsrc is not None:
            var_done = []
            self._scan_inline_desc(block, subsrc, 'vardescsearch', var_done)
            self._scan_inline_desc(block, subsrc, 'vardescsearch_fallback', var_done)

        for bvar in list(block['vars'].values()):
            bvar.setdefault('desc', '')

    # Getting info ---

    def get_module(self, block):
        """Get the name of the module including *block*"""
        while block['block'] != 'module':
            if block['parent_block'] == 'unknown':
                break
            block = block['parent_block']
        return block['name']

    def get_src(self, block):
        """Get the source lines of the file including *block*"""
        return self.src[block['from'].split(':')[0]]

    def join_src(self, src):
        """Join, in place, unended lines (``&``) with the following one"""
        for iline, line in enumerate(src):
            m = self._re_unended_match(line)
            if m:
                nextm = self._re_unstarted_match(src[iline + 1])
                src[iline] = m.group(1) + (nextm.group(1) if nextm else src[iline + 1])
                del src[iline + 1]
        return src

    def get_blocksrc(self, block, src=None, istart=0, getidx=False, stopmatch=None, exclude=None):
        """Extract the source lines of a cracked block

        :Params:
            - **block**: Cracked block.
            - **src**, optional: List of source lines including the block.
            - **istart**, optional: Start searching from this line number.
            - **getidx**, optional: Also return the indices of the first and last lines.
            - **stopmatch**, optional: Regular expression (or its ``match``) stopping the search.
            - **exclude**, optional: Types of sub-blocks to strip (see :meth:`strip_blocksrc`).

        :Return: ``None`` or a list of lines
        """
        if src is None:
            src = self.get_src(block)
        blocktype = block['block'].lower()
        blockname = re.escape(block['name'].lower())
        ftypes = r'(?:(?:%s).*\s+)?' % fortrantypes if blocktype == 'function' else ''
        prefixtype = r'(' + block['prefix'] + r')?\s*' + blocktype if 'prefix' in block else blocktype
        if blocktype == 'interface':  # special case for operator overload
            tail_start, tail_end = r'(?=\s|$|\()', r'.*$'
        else:
            tail_start, tail_end = r'\b.*$', r'\s+%s\b.*$' % blockname
        if blocktype == 'type':  # also match "type, extends(x) :: name" and "type :: name"
            rstart = re.compile(r"^\s*type(?:\s*,.*?::\s*|\s+(?:::\s*)?)%s%s" % (blockname, tail_start), re.I).match
        else:
            rstart = re.compile(r"^\s*%s%s\s+%s%s" % (ftypes, prefixtype, blockname, tail_start), re.I).match
        rend = re.compile(r"^\s*end\s+%s%s" % (prefixtype, tail_end), re.I).match
        if isinstance(stopmatch, str):
            stopmatch = re.compile(stopmatch).match

        # Beginning
        for ifirst in range(istart, len(src)):
            if stopmatch and stopmatch(src[ifirst]):
                return
            if rstart(src[ifirst]):
                break
        else:
            return

        # End
        for ilast in range(ifirst, len(src)):
            if stopmatch and stopmatch(src[ilast]):
                break
            if rend(src[ilast].lower()):
                break

        mysrc = list(src[ifirst:ilast + 1])
        self.strip_blocksrc(block, exclude, src=mysrc)
        if getidx:
            return mysrc, (ifirst, ilast)
        return mysrc

    def strip_blocksrc(self, block, exc, src=None):
        """Strip, in place, sub-blocks from source lines

        :Params:
            - **block**: Cracked block.
            - **exc**: Type (or list of types) of sub-blocks to remove.
            - **src**: List of source lines of *block*.
        """
        if exc is None:
            return
        if not isinstance(exc, list):
            exc = [exc]
        for sub in block['body']:
            if sub['block'] in exc:
                subsrc = self.get_blocksrc(sub, src=src, getidx=True)
                if subsrc is None:
                    continue  # Already stripped
                del src[subsrc[1][0]:subsrc[1][1]]

    def get_comment(self, src, iline=1, aslist=False, stripped=False, getilast=False, rightafter=True):
        """Search for and return the comment starting after ``iline`` in ``src``

        :Params:
            - **src**: A list of lines.
            - **iline**, optional: Index of first line to read.
            - **aslist**, optional: Return the comment as a list.
            - **stripped**, optional: Strip each line of comment.
            - **getilast**, optional: Return the index of the last line instead of the synopsis.
            - **rightafter**, optional: Suppose the comment right after the signature line.
              It prevents from reading a comment that is not a description of the routine.

        :Return: ``comment, synopsis`` or ``comment, ilast``
        """
        scomment = []
        synopsis = []
        if src:
            in_a_breaked_line = src[0].strip().endswith('&')
            for iline in range(iline, len(src)):
                line = src[iline].strip()
                if line.startswith('&'):  # Breaked line
                    continue

                m = self._re_comment_match(line)
                if m is None:  # Not a comment
                    if not scomment:
                        if line.endswith('&'):  # Not the end of signature
                            in_a_breaked_line = True
                            continue
                        if in_a_breaked_line:
                            in_a_breaked_line = False
                            continue
                        if not rightafter and not line:  # Empty line but we continue searching
                            continue
                    break

                comment = m.group(1)
                if stripped:
                    comment = comment.strip()
                if not scomment:  # Space prefix to remove
                    prefix = self._re_space_prefix_match(comment).group(1)
                if comment.startswith(prefix):
                    comment = comment[len(prefix):]
                if comment.lstrip().startswith(':synopsis:'):
                    synopsis.append(comment.replace(':synopsis:', ''))
                else:
                    scomment.append(comment)

        if not aslist:
            scomment = self.format_lines(scomment, nlc=' ')
            synopsis = self.format_lines(synopsis, nlc=' ')
        if getilast:
            return scomment, iline
        return scomment, synopsis

    def get_synopsis(self, block, nmax=3):
        """Get the synopsis, or the first ``nmax`` non empty lines of the description, as 1 line

        If the description has more than ``nmax`` lines, the last one is appended of '..' if it ends with a dot.
        An empty string is returned if there is nothing.
        """
        if block['synopsis']:
            return ' '.join(line.strip() for line in block['synopsis'])
        sd = []
        for line in block['desc']:
            line = line.strip()
            if not line:
                if not sd:
                    continue
                break
            sd.append(line)
            if len(sd) > nmax:
                if sd[-1].endswith('.'):
                    sd[-1] += '..'
                break
        return ' '.join(sd)

    def get_blocklist(self, choice, module, sort=True):
        """Get the list of types, variables or routines of a module that have to be documented"""
        choice = choice.lower()
        if not choice.endswith('s'):
            choice += 's'
        assert choice in ['types', 'variables', 'functions', 'subroutines', 'interfaces'], "Wrong type of declaration"
        module = module.lower()
        assert module in self.modules, "Wrong module name"
        sellist = [v for v in getattr(self, choice).values()
                   if 'module' in v and v['module'] == module and self.is_member(v)]
        if sort:
            sellist.sort(key=itemgetter('name'))
        return sellist

    def is_member(self, object):
        """Tell if a block has to be documented, according to the ``members``,
        ``undoc_members``, ``forceadd_members`` and ``exclude_private`` attributes"""
        def names(value):
            return [x.strip(' ') for x in value.split(",")]

        try:
            name = object.get('name').strip()
        except AttributeError:
            name = None
        ok = 'private' not in object.get('attrspec', []) or self.exclude_private is None
        if ok:
            if self.members:
                ok = name is None or name in names(self.members)
            if self.undoc_members:
                ok = name is None or name not in names(self.undoc_members)
        elif self.members:  # even if private, document it when explicitly listed
            ok = name in names(self.members)
        if self.forceadd_members:  # always document it when listed
            ok = ok or name in names(self.forceadd_members)
        return ok

    # Formatting ---

    def indent(self, n):
        """Get a proper indentation"""
        return n * self.ic

    @staticmethod
    def _split_lines(lines, strip):
        """Split multi-line items, expand tabs and optionally drop leading empty lines"""
        out = []
        for line in lines:
            out.extend(line.splitlines() if line else [line])
        out = [line.expandtabs(4) for line in out]
        if strip:
            while out and not out[0]:
                out.pop(0)
        return out

    @staticmethod
    def _min_indent(lines):
        """Column of the first non space character of the least indented line"""
        return min((len(line) - len(line.lstrip()) for line in lines if line.expandtabs().strip()), default=0)

    def format_lines(self, lines, indent=0, bullet=None, nlc='\n', strip=False, sublines=None):
        """Convert a list of lines to a text, reindented at level *indent*

        :Params:
            - **bullet**: Prefix of each line, ``True`` for ``-``.
            - **nlc**: New line character.
            - **strip**: Remove leading empty lines.
            - **sublines**: Lines added after *lines* with an additional indentation.
        """
        if not lines:
            return ''
        bullet = (str('-' if bullet is True else bullet) + ' ') if bullet else ''
        if isinstance(lines, str):
            lines = [lines]
        lines = self._split_lines(lines, strip)
        if not lines:
            return ''
        first = self._min_indent(lines)
        text = nlc.join(self.indent(indent) + bullet + line[first:] for line in lines) + nlc

        if sublines is not None:
            if isinstance(sublines, str):
                sublines = [sublines]
            sublines = self._split_lines(sublines, strip)
            if not sublines:
                return ''
            first = self._min_indent(sublines)
            text += nlc + nlc.join(self.indent(indent + 1) + bullet + line[first:] for line in sublines) + nlc
        return text

    def format_title(self, text, ulc=None, indent=0):
        """Create a simple rst title with indentation, underlined with *ulc* (default: :attr:`ulc`)"""
        if ulc is None:
            ulc = self.ulc
        return self.format_lines([text, ulc * len(text)], indent=indent) + '\n'

    def format_rubric(self, text, indent=0):
        """Create a simple rst rubric with indentation"""
        return self.format_lines('.. rubric:: ' + text, indent=indent) + '\n'

    def format_subsection(self, text, indent=0, **kwargs):
        """Format a subsection (title or rubric, depending on :attr:`sst`)"""
        if self.sst == 'title':
            return self.format_title(text, indent=indent, **kwargs)
        return self.format_rubric(text, indent=indent, **kwargs)

    def format_declaration(self, dectype, name, description=None, indent=0, bullet=None, options=None):
        """Create a simple rst declaration ``.. f:<dectype>:: <name>`` with options and description"""
        declaration = self.format_lines('.. f:%s:: %s' % (dectype, name), bullet=bullet, indent=indent)
        if options:
            declaration += self.format_options(options, indent=indent + 1)
        declaration += '\n'
        if description:
            declaration += self.format_lines(description, indent=indent + 1)
        return declaration + '\n'

    def format_options(self, options, indent=0):
        """Format directive options, skipping those set to ``None``"""
        return self.format_lines([':%s: %s' % option for option in options.items() if option[1] is not None],
                                 indent=indent)

    def format_funcref(self, fname, current_module=None, aliasof=None, module=None):
        """Format the reference to a module routine, type or variable

        Formatting varies whether the object is local to *current_module* and is an alias.

        :Example: ``:f:func:`~mymodule/myfunc```
        """
        fname = fname.lower()
        falias = None
        if aliasof is not None:
            falias, fname = fname, aliasof
        elif fname in self.routines and fname in self.routines[fname].get('aliases', []):
            falias, fname = fname, self.routines[fname]['name']

        # Local reference
        if module is None and fname in self.routines:
            module = self.routines[fname].get('module')
        if module is None or (current_module is not None and module == current_module):
            if falias:
                return ':f:func:`%s<%s>`' % (falias, fname)
            return ':f:func:`%s`' % fname

        # Remote reference
        kind = 'func'
        if fname in self.types or ('f:type' in fortran_invs and fname in fortran_invs['f:type']):
            kind = 'type'
        elif fname in self.variables or ('f:variable' in fortran_invs and fname in fortran_invs['f:variable']):
            kind = 'var'
        if falias:
            return ':f:%s:`%s<~%s%s%s>`' % (kind, falias, module, f_sep, falias)
        return ':f:%s:`~%s%s%s`' % (kind, module, f_sep, fname)

    def _use_funcs(self, mname, monly):
        """Format the routines imported from module *mname* (``monly`` is its ``use`` entry)"""
        funcs = []
        if monly:
            for fname, falias in list(monly['map'].items()):
                func = self.format_funcref(fname, module=mname)
                if fname != falias:
                    func = '%s ⇒ %s' % (self.format_funcref(fname), self.format_funcref(falias, module=mname))
                funcs.append(func)
        return funcs

    def format_use(self, block, indent=0, short=False):
        """Format the ``use`` statements of a block

        :Params:
            - **short**: Single ``:use:`` field. Else, lists of used (internal) and external modules.
        """
        if 'use' not in block:
            return ''

        if short:
            entries = []
            for mname, monly in list(block['use'].items()):
                funcs = self._use_funcs(mname, monly)
                entries.append(':f:mod:`%s`' % mname + (' (%s)' % ', '.join(funcs) if monly else ''))
            return self.format_lines(':use: ' + ', '.join(entries), indent)

        pad = self.indent(indent)
        internal = external = ''
        for mname, monly in list(block['use'].items()):
            line = pad + ':f:mod:`%s`' % mname
            if mname in self.modules:
                sdesc = self.get_synopsis(self.modules[mname])
                if sdesc:
                    line += ': ' + sdesc
            funcline = pad + '\n '.join(self._use_funcs(mname, monly))
            entry = self.format_lines([line], indent, bullet='-',
                                      sublines=None if funcline == '' else [funcline]) + '\n'
            if mname in self.modules:
                internal += entry
            else:
                external += entry
        use = ''
        if internal:
            use += self.format_subsection('Used modules', indent=indent) + internal
        if external:
            use += self.format_subsection('External modules', indent=indent) + external
        return use

    def format_argdim(self, block):
        """Format the dimension of a variable"""
        if 'dimension' in block:
            return '(%s)' % ', '.join(s.replace('*', '·') for s in block['dimension'])
        return ''

    def format_argattr(self, block):
        """Filter and format the attributes (optional, in/out/inout, etc) of a variable"""
        vattr = []
        if block.get('intent'):
            vattr.append('/'.join(block['intent']))
        if block.get('attrspec'):
            default_value = (block['='] if '=' in block and not block['='].startswith('shape(') else None)
            newattrs = [a for a in block['attrspec'] if not (a == 'optional' and default_value is None)]
            if default_value is not None:
                newattrs.append('default=' + default_value)
            if 'private' in newattrs and 'public' in newattrs:
                newattrs.remove('private')
            vattr.append(','.join(newattrs))
        vattr = ','.join(filter(None, vattr))
        return ' [%s]' % vattr if vattr else ''

    def format_argtype(self, block):
        """Format the type of a variable (spaces are removed for the domain regexp)"""
        if 'typespec' not in block:
            return ''
        vtype = block['typespec']
        if vtype == 'type':
            vtype = block['typename']
        elif vtype == 'double precision':
            vtype = 'double_precision'
        elif vtype == 'double complex':
            vtype = 'double_complex'
        elif vtype == 'character' and 'charselector' in block:
            cs = block['charselector']
            if 'len' in cs:
                vtype += '(len=%s)' % cs['len']
            elif '*' in cs and cs['*'] != '(*)':
                vtype += '(len=%s)' % cs['*']
            else:
                vtype += '(len=*)'
        return vtype

    def _format_field(self, role, vname, vtype, vdim, vattr, vdesc):
        return self._fmt_vardesc % dict(role=role, vname=vname, vtype=vtype, vdim=vdim, vattr=vattr, vdesc=vdesc)

    def format_argfield(self, blockvar, role=None, block=None):
        """Format the description of a variable as a domain field

        :Params:
            - **blockvar**: Variable block.
            - **role**: Field role. By default, ``r`` for the result of *block*, else ``o`` or ``p``.
        """
        vname = blockvar['name']
        if not role:
            if block and vname in [block['name'], block.get('result')]:
                role = 'r'
            else:
                role = 'o' if 'optional' in blockvar.get('attrspec', []) else 'p'
        return self._format_field(role, vname, self.format_argtype(blockvar), self.format_argdim(blockvar),
                                  self.format_argattr(blockvar), blockvar.get('desc', ''))

    def format_interfacearg(self, arg, impl):
        """Format an argument of an interface as a domain field, merging its definitions in the implementations *impl*"""
        ref = self.routines[impl[0]]['vars'][arg]
        for i in impl:
            if 'result' in self.routines[i] and arg == self.routines[i]['result']:
                self.routines[i]['vars'][arg]['result'] = arg

        # Types
        vtype = self.format_argtype(ref)
        thistype = ref.get('typespec')
        seentypes = {thistype} if thistype is not None else set()
        for i in impl[1:]:
            other = self.routines[i]['vars'][arg]
            othertype = other.get('typespec')
            if othertype is not None and othertype != thistype and othertype not in seentypes:
                vtype += ',' + self.format_argtype(other)
                seentypes.add(othertype)

        # Dimensions
        vdim = self.format_argdim(ref)
        for i in impl[1:]:
            other = self.routines[i]['vars'][arg]
            if ('dimension' in other) != ('dimension' in ref) or other.get('dimension') != ref.get('dimension'):
                vdim = '(various shapes)'
                break

        if arg == ref.get('result'):
            role = 'r'
        else:
            role = 'o' if 'optional' in ref.get('attrspec', []) else 'p'
        return self._format_field(role, arg, vtype, vdim, self.format_argattr(ref), ref.get('desc', ''))

    def format_type(self, block, indent=0, bullet=False):
        """Format the description of a module type"""
        declaration = self.format_declaration('type', block['name'], block['desc'], indent=indent,
                                              bullet=bullet) + '\n'
        vlines = [self.format_argfield(block['vars'][varname], role='f') for varname in block['sortvars']]
        return declaration + self.format_lines(vlines, indent=indent + 1) + '\n'

    def get_varopts(self, block):
        """Get options (shape, type, attrs) of a variable declaration as a dict"""
        options = OrderedDict()
        vdim = self.format_argdim(block)
        if vdim:
            options['shape'] = vdim
        options['type'] = self.format_argtype(block)
        vattr = self.format_argattr(block).strip(' []')
        if vattr:
            options['attrs'] = vattr
        return options

    def format_variable(self, block, indent=0, bullet=False):
        """Format the description of a variable: type, shape, attributes, binding and default value"""
        options = self.get_varopts(block)
        varname = str(block['name']) if 'name' in block else None
        typeshape = ':Type: ' + options.pop('type') if 'type' in options else ''
        typeshape += (options.pop('shape').replace(':', '•') if 'shape' in options else '') + '\n\n'
        description = block.get('desc', '')

        # Attributes, binding and default value
        attrs = None
        if 'attrs' in options:
            attrs = []
            parts = re.split(r"default=", options.pop('attrs'))
            match = _BIND_RE.search(parts[0])
            if match:
                parts[0] = parts[0].replace(match.group(0), '')
            if parts[0].strip(',') != '':
                attrs.append(re.sub(r",\s*", ", ", ':Attributes: ' + parts[0].strip(',')))
            if match:
                attrs.append(':Bindings: Language = **%s**, Name = **%s** ' % match.groups())
            if len(parts) > 1:
                attrs.append(':Default: ' + parts[1].strip(','))

        # Fields written in the description as ":something varname:`something else`"
        if varname is not None:
            pattern = r':([\w\s]+) %s:`([^`]+)`' % re.escape(varname)
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                item = ':%s: %s' % match.groups()
                attrs = [item] if attrs is None else attrs + [item]
                description = re.sub(pattern, '', description, flags=re.IGNORECASE)
        attrtext = '' if attrs is None else '\n'.join(line for line in attrs if line.strip()) + '\n\n'

        if 'name' not in block:
            return ''
        return self.format_declaration('variable', block['name'],
                                       description=description + '\n\n' + typeshape + attrtext,
                                       options=options, indent=indent, bullet=bullet)

    def format_signature(self, block):
        """Format the arguments of a routine, with brackets around the optional ones"""
        signature = ''
        previous_optional = False
        for i, var in enumerate(block['args']):
            bvar = block['vars'][var]
            optional = 'optional' in bvar['attrspec'] and '=' not in bvar if 'attrspec' in bvar else False
            signature += '[' if optional and not previous_optional else ''
            previous_optional = optional
            signature += ', ' if i else ''
            signature += var
        return signature + (']' if previous_optional else '')

    def format_interface(self, block):
        """Format the arguments of an interface, from all its implementations"""
        args = OrderedDict()
        opts = OrderedDict()
        for name in block['implementedby']:
            for a in self.routines[name]['args']:
                if 'optional' in self.routines[name]['vars'][a].get('attrspec', []):
                    opts.setdefault(a)
                else:
                    args.setdefault(a)
        signature = ', '.join(args)
        if opts:
            signature += '[' + (', ' if args else '') + ', '.join(opts) + ']'
        return signature

    def format_routine(self, block, indent=0):
        """Format the description of a function, a subroutine, an interface or a program

        :Params:
            - **block**: Cracked block, or the name of a program or routine.
        """
        # Resolve and check block
        if isinstance(block, str):
            if block in self.programs:
                block = self.programs[block]
            elif block in self.routines:
                block = self.routines[block]
            else:
                raise F90toRstException('Unknown function, subroutine or program: %s' % block)
        elif not any(block['name'] in d for d in (self.modules, self.routines, self.programs)):
            raise F90toRstException('Unknown %s: %s' % (block['block'], block['name']))
        name = block['name']
        blocktype = block['block']

        # Declaration
        signature = ''
        if blocktype in ('subroutine', 'function'):
            signature = '(%s)' % self.format_signature(block)
        elif blocktype == 'interface':
            signature = '(%s)' % self.format_interface(block)
        declaration = self.format_declaration(blocktype, name + signature, indent=indent)

        # Comments, with C bindings
        attrs = ''
        if block.get('bindlang'):
            listbinds = block['bindlang']
            attrs = self.format_lines([':Bindings: ']) + self.format_lines(
                ['Language = **%s**, Name = **%s** ' % (lang, cname) for lang, cname in listbinds],
                bullet=len(listbinds) > 1, indent=indent + 1)
        comments = list(block['desc']) + ['']
        if comments == [''] and name in backup_desc:
            comments = list(backup_desc[name]) + ['']
        comments.append(attrs)

        if blocktype in ('subroutine', 'function'):
            # Move "@param name: description" lines to the description of variables
            regexes = [(key, re.compile(r'^\s*@param\w*\s+(?P<varname>%s)\s*[:\-–—]\s*(?P<vardesc>.+)' % key).match)
                       for key in block['vars']]
            iline = 0
            while iline < len(comments):
                for key, match in regexes:
                    m = match(comments[iline])
                    if m and key != '':
                        block['vars'][key]['desc'] += ' ' + m.group('vardesc')
                        comments.pop(iline)
                        break
                else:
                    iline += 1
            for varname in dict.fromkeys(block['args'] + block['sortvars']):
                comments.append(self.format_argfield(block['vars'][varname], block=block))

        elif blocktype == 'interface':
            args = {}
            for impl_name in block['implementedby']:
                listargs = self.routines[impl_name]['args'][:]
                if 'result' in self.routines[impl_name]:
                    listargs.append(self.routines[impl_name]['result'])
                for a in listargs:
                    args.setdefault(a, []).append(impl_name)
            for a, impl in args.items():
                comments.append(self.format_interfacearg(a, impl))

        return (declaration + self.format_lines(comments, indent + 1) +
                self.format_use(block, indent=indent + 1, short=True) + '\n\n')

    format_function = format_routine
    format_subroutine = format_routine

    def format_quickaccess(self, block, indent=0):
        """Format an abstract of all types, variables and routines of a module"""
        decs = []
        types = ', '.join(':f:type:`%s`' % sub['name'] for sub in block['body']
                          if sub['block'] == 'type' and self.is_member(sub))
        if types:
            decs.append(':Types: ' + types)
        if block['vars']:
            variables = ', '.join(':f:var:`%s`' % vv for vv in sorted(block['sortvars'])
                                  if 'name' in block['vars'][vv] and self.is_member(block['vars'][vv]))
            if variables:
                decs.append(':Variables: ' + variables)
        fdecs = sorted(sub['name'] for sub in block['body']
                       if sub['block'] in ('function', 'subroutine', 'interface') and self.is_member(sub))
        if fdecs:
            decs.append(':Routines: ' + ', '.join(':f:func:`%s`' % ff for ff in fdecs))
        if decs:
            return self.format_lines(self.format_subsection('Quick access', indent=indent) + '\n' +
                                     '\n'.join(decs)) + '\n\n'
        return ''

    def format_types(self, block, indent=0):
        """Format the description of all types of a module"""
        types = [self.format_type(sub, indent=indent) for sub in block['body']
                 if sub['block'] == 'type' and self.is_member(sub)]
        if types:
            return self.format_subsection('Types', indent=indent) + '\n'.join(types)
        return ''

    def format_variables(self, block, indent=0, ownSection=False):
        """Format the description of all variables of a block

        :Params:
            - **block**: Cracked block or, if *ownSection*, the name of a module.
            - **ownSection**: Prefix the output with the list of variables and do not add a subsection title.
        """
        variables = ''
        if ownSection:
            block = self.modules[block]
            variables += ', '.join(':f:var:`%s`' % vv for vv in block['sortvars']
                                   if 'name' in block['vars'][vv] and self.is_member(block['vars'][vv]))
            variables += '\n\n'
        if block['vars']:
            varnames = block['sortvars']
            if block['block'] == 'module':
                varnames.sort()
            for varname in varnames:
                bvar = block['vars'][varname]
                if self.is_member(bvar):
                    variables += self.format_variable(bvar, indent=indent)
            if variables:
                if ownSection:
                    variables += '\n\n'
                else:
                    variables = self.format_subsection('Variables', indent=indent) + variables + '\n\n'
        return variables

    def _format_section(self, title, lines, indent):
        """Format a subsection made of *lines*, if any"""
        if not lines:
            return ''
        return self.format_subsection(title, indent=indent) + self.format_lines(lines, indent=indent, strip=True) + '\n'

    def format_synopsis(self, block, indent=0):
        """Format the synopsis of a block"""
        return self._format_section('Synopsis', block['synopsis'], indent)

    def format_description(self, block, indent=0):
        """Format the description of a block"""
        return self._format_section('Description', block['desc'], indent)

    def format_routines(self, block, indent=0):
        """Format all functions, subroutines and interfaces of a module (or of a list of blocks)"""
        blocks = block if isinstance(block, list) else block['body']
        fdecs = [self.format_routine(sub, indent) for sub in blocks
                 if sub['block'] in ('function', 'subroutine', 'interface') and self.is_member(sub)]
        if fdecs:
            return self.format_subsection('Subroutines and functions', indent=indent) + '\n'.join(fdecs)
        return ''

    def format_module(self, block, indent=0, print_synopsis=False):
        """Format a module and its declarations

        :Params:
            - **block**: Cracked block or name of the module.
            - **print_synopsis**: Add the synopsis section before the description.
        """
        if isinstance(block, str):
            if block not in self.modules:
                raise F90toRstException('Unknown module: %s' % block)
            block = self.modules[block]
        elif block['name'] not in self.modules:
            raise F90toRstException('Unknown module: %s' % block['name'])

        declaration = self.format_declaration(
            'module', block['name'], indent=indent,
            options=dict(synopsis=self.get_synopsis(block).strip() or None))
        if self.hide_output:
            return declaration

        parts = [declaration]
        if print_synopsis:
            parts.append(self.format_synopsis(block, indent=indent))
        parts += [self.format_description(block, indent=indent),
                  self.format_quickaccess(block, indent=indent),
                  self.format_use(block, indent=indent),
                  self.format_types(block, indent=indent),
                  self.format_variables(block, indent=indent),
                  self.format_routines(block, indent=indent)]
        return ''.join(parts)

    def format_srcfile(self, srcfile, indent=0, objtype=None, search_mode='basename'):
        """Format all declarations of a file: program, module, then functions and subroutines

        :Params:
            - **objtype**, optional: Restrict to one or a list of ``"program"``, ``"module"``,
              ``"function"``, ``"subroutine"``.
        """
        rst = ''
        if objtype is not None and not isinstance(objtype, (list, tuple)):
            objtype = [objtype]

        if objtype is None or 'program' in objtype:
            bprog = self.filter_by_srcfile(srcfile, objtype='program', mode=search_mode)
            if bprog:
                rst += self.format_subsection('Program', indent=indent) + '\n'
                rst += self.format_routine(bprog[0], indent=indent) + '\n'

        if objtype is None or 'module' in objtype:
            bmod = self.filter_by_srcfile(srcfile, objtype='module', mode=search_mode)
            if bmod:
                rst += self.format_subsection('Module', indent=indent) + '\n'
                rst += self.format_module(bmod[0], indent=indent) + '\n'

        oo = [o for o in ('function', 'subroutine') if o in objtype] if objtype is not None \
            else ['function', 'subroutine']
        if oo:
            brouts = self.filter_by_srcfile(srcfile, objtype=oo, mode=search_mode)
            rst += self.format_routines(brouts, indent=indent) + '\n'
        return rst

    def __getitem__(self, module):
        return self.format_module(self.modules[module])


# Sphinx directives ---

def list_files(fortran_src, exts=('f', 'f90', 'f95'), absolute=True):
    """Get the sorted list of Fortran files

    :Params:
        - **fortran_src**: List of files, globs and directories.
        - **exts**: Extensions searched in directories, whatever their case.
        - **absolute**: Return absolute paths.
    """
    exts = {x for e in exts for x in (e, e.lower(), e.upper())}
    ffiles = []
    for fg in fortran_src:
        if not isinstance(fg, str):
            continue
        if os.path.isdir(fg):
            for ext in exts:
                ffiles.extend(glob(os.path.join(fg, '*.' + ext)))
        else:
            ffiles.extend(glob(fg))
    if absolute:
        ffiles = [os.path.abspath(ffile) for ffile in ffiles]
    ffiles.sort()
    return ffiles


def fmt_indent(string):
    """Convert an indentation specification (integer, ``"tab"``, ``"space"`` or string) to a string"""
    if string is None:
        return
    if isinstance(string, int):
        string = ' ' * string
    if string == 'tab':
        string = '\t'
    elif string == 'space':
        string = ' '
    return string


def fortran_parse(app):
    """Parse the Fortran sources of the ``fortran_src`` config value on ``builder-inited``.

    The resulting :class:`F90toRst` is stored in ``app.config._f90torst``."""
    if not isinstance(app.config.fortran_src, (str, list)):
        logger.warning("wrong list of fortran 90 source specifications: " + str(app.config.fortran_src))
        app.config._f90torst = None
        return

    logger.info(bold('parsing fortran sources...'), nonl=True)
    if not isinstance(app.config.fortran_src, list):
        app.config.fortran_src = [app.config.fortran_src]
    ffiles = list_files(app.config.fortran_src, app.config.fortran_ext)
    if not ffiles:
        logger.info(" no fortran files found")
        app.config._f90torst = None
    else:
        app.config.fortran_indent = fmt_indent(app.config.fortran_indent)
        app.config._f90torst = F90toRst(
            ffiles,
            ic=app.config.fortran_indent,
            ulc=app.config.fortran_title_underline,
            encoding=app.config.fortran_encoding)
        logger.info(' done')
    app._status.flush()


def load_intersphinx_inventories(app):
    """Fill :data:`fortran_invs` from the intersphinx inventories that contain Fortran objects"""
    global fortran_invs
    fortran_invs = {}
    all_invs = app.env.intersphinx_named_inventory
    ftypes = ('f:module', 'f:subroutine', 'f:function', 'f:variable', 'f:type', 'f:interface')
    for inv in [inv for inv in all_invs if any(t in all_invs[inv] for t in ftypes)]:
        for jkey in all_invs[inv]:
            fortran_invs[jkey] = [ikey.split('/')[-1] for ikey in all_invs[inv][jkey]]


class FortranAutoDirective(Directive):
    """Base class of the auto directives: get the parsed sources and insert generated rst"""

    def _get_f90torst(self):
        return self.state.document.settings.env.config._f90torst

    def _warn(self, msg):
        self.state_machine.reporter.warning(msg, line=self.lineno)

    def _insert(self, raw_text):
        source = self.state_machine.input_lines.source(self.lineno - self.state_machine.input_offset - 1)
        self.state_machine.insert_input(string2lines(raw_text, convert_whitespace=1), source)


class FortranAutoModuleDirective(FortranAutoDirective):
    """Document a whole module. Options change temporarily the attributes of :class:`F90toRst`."""
    has_content = True
    option_spec = {'title_underline': unchanged, 'indent': fmt_indent,
                   'subsection_type': unchanged, 'members': unchanged,
                   'undoc-members': unchanged, 'forceadd-members': unchanged,
                   'include-private': unchanged, 'hide-output': unchanged}
    required_arguments = 1
    optional_arguments = 0
    _attropts = [('ic', 'indent'), ('ulc', 'title_underline'), ('sst', 'subsection_type'),
                 ('members', 'members'), ('undoc_members', 'undoc-members'),
                 ('forceadd_members', 'forceadd-members'), ('exclude_private', 'include-private'),
                 ('hide_output', 'hide-output')]

    def _format(self, f90torst, module):
        return f90torst.format_module(module)

    def run(self):
        f90torst = self._get_f90torst()
        if f90torst is None:
            return []
        module = self.arguments[0]
        if module not in f90torst.modules:
            self._warn('Wrong fortran module name: ' + module)

        previous = {}
        for attr, opt in self._attropts:
            if self.options.get(opt):
                previous[attr] = getattr(f90torst, attr)
                setattr(f90torst, attr, self.options[opt])
        try:
            self._insert(self._format(f90torst, module))
        finally:
            for attr, value in previous.items():
                setattr(f90torst, attr, value)
        return []


class FortranAutoModvarsDirective(FortranAutoModuleDirective):
    """Document the variables of a module only."""

    def _format(self, f90torst, module):
        return f90torst.format_variables(module, ownSection=True)


class FortranAutoObjectDirective(FortranAutoDirective):
    """Generic directive for fortran object auto-documentation

    Redefine :attr:`_warning` and :attr:`_objtype` attribute when subclassing.

    .. attribute:: _warning

        Warning message when object is not found, like ``'Wrong function or subroutine name: %s'``.

    .. attribute:: _objtype

        Type of fortran object.
        If "toto" is set as object type, then :class:`F90toRst` must have
        attribute :attr:`totos` containing index of all related fortran objects,
        and method :meth:`format_toto` for formatting the object.
    """
    has_content = False
    option_spec = OrderedDict()
    required_arguments = 1
    optional_arguments = 0
    _warning = 'Wrong routine name: %s'
    _objtype = 'routine'

    def run(self):
        f90torst = self._get_f90torst()
        if f90torst is None:
            return []

        objname = self.arguments[0].lower()
        if f_sep in objname:
            objname = objname.split(f_sep)[-1]  # remove module name
        objects = getattr(f90torst, self._objtype + 's')
        if objname not in objects:
            self._warn(self._warning % objname)

        block = objects[objname]
        raw_text = getattr(f90torst, 'format_' + self._objtype)(block)
        if 'parent_block' in block:  # inside a module
            raw_text = '.. f:currentmodule:: %s\n\n' % block['parent_block']['name'] + raw_text
        self._insert(raw_text)
        return []


class FortranAutoFunctionDirective(FortranAutoObjectDirective):
    """Document a function."""
    _warning = 'Wrong function name: %s'
    _objtype = 'function'


class FortranAutoSubroutineDirective(FortranAutoObjectDirective):
    """Document a subroutine."""
    _warning = 'Wrong subroutine name: %s'
    _objtype = 'subroutine'


class FortranAutoInterfaceDirective(FortranAutoObjectDirective):
    """Document an interface."""
    _warning = 'Wrong interface name: %s'
    _objtype = 'interface'


class FortranAutoTypeDirective(FortranAutoObjectDirective):
    """Document a type."""
    _warning = 'Wrong type name: %s'
    _objtype = 'type'


class FortranAutoVariableDirective(FortranAutoObjectDirective):
    """Document a module variable."""
    _warning = 'Wrong variable name: %s'
    _objtype = 'variable'


class FortranAutoProgramDirective(FortranAutoDirective):
    """Document a program."""
    has_content = False
    option_spec = OrderedDict()
    required_arguments = 1
    optional_arguments = 0

    def run(self):
        f90torst = self._get_f90torst()
        if f90torst is None:
            return []
        program = self.arguments[0].lower()
        if program not in f90torst.programs:
            self._warn('Wrong program name: ' + program)
        self._insert(f90torst.format_routine(program))
        return []


class FortranAutoSrcfileDirective(FortranAutoDirective):
    """Document the content of a source file."""
    has_content = False
    option_spec = dict(search_mode=unchanged, objtype=unchanged)
    required_arguments = 1
    optional_arguments = 0

    def run(self):
        f90torst = self._get_f90torst()
        if f90torst is None:
            return []
        objtype = self.options.get('objtype')
        if objtype:
            objtype = objtype.split(' ,')
        srcfile = self.arguments[0].lower()
        raw_text = f90torst.format_srcfile(srcfile, search_mode=self.options.get('search_mode'), objtype=objtype)
        if not raw_text:
            self._warn('No valid content found for file: ' + srcfile)
        self._insert(raw_text)
        return []


def setup(app):
    """Sphinx entry point: register object types, config values, directives and event handlers"""
    app.add_object_type('ftype', 'ftype', indextemplate='pair: %s; Fortran type')
    app.add_object_type('fvar', 'fvar', indextemplate='pair: %s; Fortran variable')

    app.add_config_value('fortran_title_underline', '-', False)
    app.add_config_value('fortran_indent', 4, False)
    app.add_config_value('fortran_subsection_type', 'rubric', False)
    app.add_config_value('fortran_src', ['.'], False)
    app.add_config_value('fortran_ext', ['f90', 'f95'], False)
    app.add_config_value('fortran_encoding', 'utf8', False)

    FortranDomain.directives.update(
        automodule=FortranAutoModuleDirective,
        autoroutine=FortranAutoObjectDirective,
        autotype=FortranAutoTypeDirective,
        autovariable=FortranAutoVariableDirective,
        autofunction=FortranAutoFunctionDirective,
        autosubroutine=FortranAutoSubroutineDirective,
        autointerface=FortranAutoInterfaceDirective,
        autoprogram=FortranAutoProgramDirective,
        autosrcfile=FortranAutoSrcfileDirective,
        automodvars=FortranAutoModvarsDirective,
    )
    app.connect('builder-inited', fortran_parse)
    app.connect('builder-inited', load_intersphinx_inventories)
