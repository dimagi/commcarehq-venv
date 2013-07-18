#!/usr/local/bin/python

""" Distutils Extensions needed for the mx Extensions.

    Copyright (c) 1997-2000, Marc-Andre Lemburg; mailto:mal@lemburg.com
    Copyright (c) 2000-2013, eGenix.com Software GmbH; mailto:info@egenix.com
    See the documentation for further information on copyrights,
    or contact the author. All Rights Reserved.
"""
#
# History:
# 3.8.0: Changed to prebuilt filename version 2
# 3.7.0: Added mx_register command with option to add a hash tag
#        to the download_url (--with-hash-tag)
# 3.6.8: Removed mx_customize_compiler(). We now always use distutils'
#        version. See #943.
# 3.6.7: Fix for clang override needed for Mac OS X Lion (see #943)
# 3.6.6: Fix for moved customize_compiler() function (see #861)
# 3.6.5: added install option --force-non-pure
# 3.6.4: import commands and base classes directly from setuptools,
#        if present to fixes compatibility with pip (see #741)
# 3.6.3: added verify_package_version()
# 3.6.2: added fix-up for distutils.util.change_root()
# 3.6.1: added --exclude-files to bdist_prebuilt
# 3.6.0: added support for Python 2.7's distutils version
# 3.5.1: added support to have prebuilt archives detect version and
#        and platform mismatches before installing a package
# 3.5.0: added own non-setuptools version of bdist_egg to build eggs
#        straight from the available packages rather than relying on
#        setuptools to do this
# 3.4.2: added support for using embedded .dylibs
# 3.4.1: only include top-level documentation directories in prebuilt archives
# 3.4.0: made the inclusion of the data source files optional in bdist_prebuilt,
#        fixed the prebuilt file search mechanism to always convert to platform
#        convention
# 3.3.1: have mx_version()'s snapshot default to true if prerelease is 'dev'
# 3.3.0: use our own mx_get_platform() version in order to support prebuilt
#        installers on platforms that have slightly different platform strings
# 3.2.1: py_version() will no longer add the Unicode info on Windows
# 3.2.0: Add support for Python 2.6 Windows builds
# 3.1.1: Allow Unicode values for meta data
# 3.1.0: changed the build pickle name used by prebuilt archives
# 3.0.0: added mx_build_data, removed the need to use "build --skip"
#        when installing prebuilt archives, uninstall now also works
#        for prebuilt archives
# 2.9.0: added support for (orig, dest) data_files definitions
# 2.8.0: added optional setuptools support
# 2.7.0: added mx_bdist_prebuilt
# 2.6.0: added mx_bdist_msi that allows setting the product name
# 2.5.1: add support for distutils 2.5.0 which broke the MSVCCompiler
#        compile options hack
# 2.5.0: patch install_lib to not produce weird byte-code filenames;
#        add work-around for change in bdist_wininst introduced in
#        Python 2.4 that broke the py_version() approach
# 2.4.0: remove monkey patch and make use of py_version() instead
# 2.3.0: monkey patch get_platform() to include the Unicode width info
# 2.2.0: replaced .announce() and .warn() usage with log object
# 2.1.2: added wide Unicode support
# 2.1.1: added support for Python 2.3 way of finding MSVC paths
# 2.1.0: added bdist_zope, support for classifiers
# 2.0.0: reworked the include and lib path logic; factored out the
#        compiler preparation
# 1.9.0: added new include and lib path logic; added bdist_zope command
# Older revisions are not documented.
#
import types, glob, os, sys, re, cPickle, copy, imp, shutil, urllib2

### Globals

# Module version
__version__ = '3.8.0'

# Generate debug output for mxSetup.py ?
_debug = int(os.environ.get('EGENIX_MXSETUP_DEBUG', 0))

# Python version running this module
python_version = sys.version[:3]

# Prebuilt archive marker file
PREBUILT_MARKER = 'PREBUILT'

# Allowed configuration value types; all other configuration entries
# are removed by run_setup()
ALLOWED_SETUP_TYPES = (types.StringType,
                       types.ListType,
                       types.TupleType,
                       types.IntType,
                       types.FloatType)
if python_version >= '2.6':
    ALLOWED_SETUP_TYPES += (types.UnicodeType,)

# Some Python distutils versions don't support all setup keywords we
# use
UNSUPPORTED_SETUP_KEYWORDS = ()
if python_version < '2.3':
    UNSUPPORTED_SETUP_KEYWORDS = UNSUPPORTED_SETUP_KEYWORDS + (
        'classifiers',
        'download_url',
        )

# Filename suffixes used for Python modules on this platform
PY_SUFFIXES = [suffix for (suffix, mode, order) in imp.get_suffixes()]
if '.pyc' not in PY_SUFFIXES:
    PY_SUFFIXES.append('.pyc')
if '.pyo' not in PY_SUFFIXES:
    PY_SUFFIXES.append('.pyo')

# Namespace __init__.py file content required by setuptools namespace
# packages
SETUPTOOLS_NAMESPACE_INIT = """\
__import__('pkg_resources').declare_namespace(__name__)
"""
    
### Python compatibility support

if 1:
    # Patch True/False into builtins for those versions of Python that
    # don't support it
    try:
        True
    except NameError:
        __builtins__['True'] = 1
        __builtins__['False'] = 0

    # StringTypes into types module for those versions of Python that
    # don't support it
    try:
        types.StringTypes
    except AttributeError:
        types.StringTypes = (types.StringType, types.UnicodeType)

    # Patch isinstance() to support tuple arguments
    try:
        isinstance('', types.StringTypes)
    except TypeError:
        def py22_isinstance(obj, classes,
                            orig_isinstance=isinstance):
            if type(classes) is not types.TupleType:
                return orig_isinstance(obj, classes)
            for classobj in classes:
                if orig_isinstance(obj, classobj):
                    return True
            return False
        __builtins__['isinstance'] = py22_isinstance

    # UnicodeDecodeError is new in Python 2.3
    try:
        UnicodeDecodeError
    except NameError:
        UnicodeDecodeError = UnicodeError

if python_version < '2.2':
    def module_loaded(name):
        return sys.modules.has_key(name)
    def has_substring(substr, text):
        return text.find(substr) >= 0
else:
    def module_loaded(name):
        return name in sys.modules
    def has_substring(substr, text):
        return substr in text

### distutils fix-ups

# distutils.util.change_root() has a bug on nt and os2: it fails with
# an IndexError in case pathname is empty. We fix this by
# monkey-patching distutils.
        
import distutils.util

orig_change_root = distutils.util.change_root

def change_root(new_root, pathname):
    if os.name == 'nt':
        (drive, path) = os.path.splitdrive(pathname)
        if path and path[0] == '\\':
            path = path[1:]
        return os.path.join(new_root, path)
    elif os.name == 'os2':
        (drive, path) = os.path.splitdrive(pathname)
        if path and path[0] == os.sep:
            path = path[1:]
        return os.path.join(new_root, path)
    else:
        return orig_change_root(new_root, pathname)

distutils.util.change_root = change_root

### Setuptools support

# Let setuptools monkey-patch distutils, if a command-line option
# --use-setuptools is given and enable the setuptools work-arounds
# if it was already loaded (see ticket #547).
if module_loaded('setuptools'):
    import setuptools
elif '--use-setuptools' in sys.argv:
    sys.argv.remove('--use-setuptools')
    try:
        import setuptools
        print 'running mxSetup.py with setuptools patched distutils'
    except ImportError:
        print 'could not import setuptools; ignoring --use-setuptools'
        setuptools = None
else:
    setuptools = None

### Distutils platform support

import distutils.util

if not hasattr(distutils.util, 'set_platform'):
    # Replace the distutils get_platform() function with our own, since we
    # will in some cases need to adjust its return value, e.g. for
    # pre-built archives.
    orig_get_platform = distutils.util.get_platform

    # Global platform string
    PLATFORM = orig_get_platform()

    def mx_get_platform():

        """ Return the platform string that distutils uses through-out
            the system.

        """
        return PLATFORM

    # Replace distutils' own get_platform() function
    distutils.util.get_platform = mx_get_platform

    def mx_set_platform(platform):

        """ Adjust the platform string that distutils uses to platform.

            This is needed e.g. when installing pre-built setups, since
            the target system platform string may well be different from
            the build system one, e.g. due to OS version differences or
            Mac OS X fat binaries that get installed on i386/ppc systems.

        """
        global PLATFORM
        if PLATFORM != platform:
            log.info('adjusting distutils platform string to %r' % platform)
            PLATFORM = platform

else:
    # For Python 2.7+ and 3.2+ we don't need to monkey-patch
    # distutils, since it now has a set_platform() API.
    #
    # XXX Turns out that this useful functionality was removed again,
    #     before 2.7 and 3.2 were released. See the discussion on
    #     http://bugs.python.org/issue13994 and #861. Leaving the code
    #     here in case it gets added again.

    def mx_get_platform():

        """ Return the platform string that distutils uses through-out
            the system.

        """
        return distutils.util.get_platform()

    def mx_set_platform(platform):

        """ Adjust the platform string that distutils uses to platform.

            This is needed e.g. when installing pre-built setups, since
            the target system platform string may well be different from
            the build system one, e.g. due to OS version differences or
            Mac OS X fat binaries that get installed on i386/ppc systems.

        """
        if platform != mx_get_platform():
            log.info('adjusting distutils platform string to %r' % platform)
            distutils.util.set_platform(platform)

### Load distutils

# This has to be done after importing setuptools, since it heavily
# monkey-patches distutils with its black magic...

from distutils.errors import \
     DistutilsError, DistutilsExecError, CompileError, CCompilerError, \
     DistutilsSetupError
if setuptools is not None:
    from setuptools import setup, Extension, Command
    from setuptools import Distribution
    from setuptools.command.install import install
else:
    from distutils.core import setup, Extension, Command
    from distutils.dist import Distribution
    from distutils.command.install import install
from distutils.msvccompiler import MSVCCompiler
from distutils.util import execute
from distutils.version import StrictVersion
from distutils.dir_util import remove_tree, mkpath, create_tree
from distutils.spawn import spawn, find_executable
from distutils.command.config import config
from distutils.command.build import build
from distutils.command.build_ext import build_ext
from distutils.command.build_clib import build_clib
from distutils.command.build_py import build_py
from distutils.command.bdist import bdist
from distutils.command.bdist_rpm import bdist_rpm
from distutils.command.bdist_dumb import bdist_dumb
from distutils.command.bdist_wininst import bdist_wininst
from distutils.command.install_data import install_data
from distutils.command.install_lib import install_lib
from distutils.command.sdist import sdist
from distutils.command.register import register
from distutils.command.clean import clean
import distutils.archive_util

# distutils changed a lot in Python 2.7/3.2 due to many
# distutils.sysconfig APIs having been moved to the new (top-level)
# sysconfig module.
if (python_version < '2.7' or
    (python_version >= '3.0' and python_version < '3.2')):
    # Older Python versions (<=2.6 and <=3.1):
    from distutils.sysconfig import \
         get_config_h_filename, parse_config_h, customize_compiler, \
         get_config_vars, get_python_version
    from distutils.util import get_platform

else:
    # More recent Python versions (2.7 and 3.2+):
    from sysconfig import \
         get_config_h_filename, parse_config_h, get_path, \
         get_config_vars, get_python_version, get_platform

    # This API was moved from distutils.sysconfig to
    # distutils.ccompiler in Python 2.7... and then back again in
    # 2.7.3 (see #861); since the sysconfig version is deemed the
    # correct one and 3.x only has it there, we first try sysconfig
    # now and then revert to ccompiler in case it's not found
    try:
        from distutils.sysconfig import customize_compiler
    except ImportError:
        from distutils.ccompiler import customize_compiler


def get_python_include_dir():

    """ Return the path to the Python include dir.

        This is the location of the Python.h and other files.

    """
    # Can't use get_path('include') here, because Debian/Ubuntu
    # hack those paths to point to different installation paths
    # rather than the Python's own paths. See #762.
    try:
        config_h = get_config_h_filename()
        include_dir = os.path.split(config_h)[0]
        if not os.path.exists(os.path.join(include_dir, 'Python.h')):
            raise IOError('Python.h not found in include dir %s' %
                          include_dir)
        return include_dir

    except IOError, reason:
        if _debug:
            print 'get_config_h_filename: %s' % reason
        # Ok, we've hit a problem with the Python installation or
        # virtualenv setup, so let's try a common locations:
        pydir = 'python%i.%i' % (sys.version_info[0], sys.version_info[1])
        for dir in (
            os.path.join(sys.prefix, 'include', pydir),
            os.path.join(sys.prefix, 'include', 'python'),
            os.path.join(sys.prefix, 'include'),
            os.path.join(sys.exec_prefix, 'include', pydir),
            os.path.join(sys.exec_prefix, 'include', 'python'),
            os.path.join(sys.exec_prefix, 'include'),
            ):
            if _debug > 1:
                print ('get_config_h_filename: trying include dir: %s' %
                       dir)
            if os.path.exists(os.path.join(dir, 'Python.h')):
                if _debug:
                    print ('get_config_h_filename: found include dir: %s' %
                           dir)
                return dir
        # Nothing much we can do...
        raise

### Optional distutils support

# Load the MSI bdist command (new in Python 2.5, only on Windows)
try:
    from distutils.command.bdist_msi import bdist_msi
    import msilib
except ImportError:
    bdist_msi = None

# The log object was added to distutils in Python 2.3; we provide a
# compatile emulation for earlier Python versions
try:
    from distutils import log
except ImportError:
    class Log:
        def log(self, level, msg, *args):
            print msg % args
            sys.stdout.flush()
        def debug(self, msg, *args):
            if _debug:
                self.log(1, msg, args)
        def info(self, msg, *args):
            if _debug:
                self.log(2, msg, args)
        def warn(self, msg, *args):
            self.log(3, msg, args)
        def error(self, msg, *args):
            self.log(4, msg, args)
        def fatal(self, msg, *args):
            self.log(5, msg, args)
    log = Log()

### Third-party distutils extensions

# This is bdist_ppm from ActiveState
if python_version >= '2.0':
    try:
        from distutils.command import bdist_ppm
    except ImportError:
        bdist_ppm = None
    try:
        from distutils.command import GenPPD
    except ImportError:
        GenPPD = None
else:
    bdist_ppm = None
    GenPPD = None

###

#
# Helpers
#

def fetch_url(url, timeout=30):

    """ Fetch the given url and return the data as string.

        The function can raise urllib2.URLError exceptions in case of
        an error.

    """
    if python_version >= '2.6':
        data = urllib2.urlopen(url, None, timeout)
    elif python_version >= '2.3':
        import socket
        socket.setdefaulttimeout(timeout)
        data = urllib2.urlopen(url)
    else:
        # Ignore timeout
        data = urllib2.urlopen(url)
    return data.read()

def mx_download_url(download_url, mode='simple'):

    """ Add a hash marker to the download_url.

        This is done by fetching the URL, creating
        one or more hash/size entries and appending these
        as fragment to the download_url.

        mode determines how the fragment is formatted. Possible
        values:
        
        * 'simple': add #md5=...
        
          This is compatible with setuptools/easy_install/pip.

        * 'pip': add #sha256=...

          This is compatible with pip only. setuptools/easy_install
          don't support sha256 hashes.

        * 'extended': add #md5=...&sha1=...&sha256=...&size=...

          This is not yet supported by the installers tools, but
          provides the most advanced hash tag format. sha256 is only
          included if supported by the Python version.

    """
    if python_version >= '2.5':
        import hashlib
        md5 = hashlib.md5
        sha1 = hashlib.sha1
        sha256 = hashlib.sha256
    else:
        import md5, sha
        md5 = md5.md5
        sha1 = sha.sha
        sha256 = None
    data = fetch_url(download_url)
    if mode == 'simple':
        return '%s#md5=%s' % (
            download_url,
            md5(data).hexdigest())
    elif mode == 'pip':
        if sha256 is None:
            raise TypeError('Python version does not support SHA-256')
        return '%s#sha256=%s' % (
            download_url,
            sha256(data).hexdigest())
    elif mode == 'extended':
        if sha256 is not None:
            return '%s#md5=%s&sha1=%s&sha256=%s&size=%i' % (
                download_url,
                md5(data).hexdigest(),
                sha1(data).hexdigest(),
                sha256(data).hexdigest(),
                len(data))
        else:
            return '%s#md5=%s&sha1=%s&size=%i' % (
                download_url,
                md5(data).hexdigest(),
                sha1(data).hexdigest(),
                len(data))

def _test_mx_download_url():
    for url in (
        'file:///home/lemburg/projects/distribution/index/ucs2/egenix-pyopenssl/0.13.0_1.0.1c_1/index.html',
        'http://downloads.egenix.com/python/index/ucs2/egenix-pyopenssl/0.13.0_1.0.1c_1/',
        'http://downloads.egenix.com/python/index/ucs2/egenix-pyopenssl/0.13.0_1.0.1c_1/index.html',
        'https://downloads.egenix.com/python/index/ucs2/egenix-pyopenssl/0.13.0_1.0.1c_1/',
        'https://downloads.egenix.com/python/index/ucs2/egenix-pyopenssl/0.13.0_1.0.1c_1/index.html',
        ):
        print mx_download_url(url)
        print mx_download_url(url, 'simple')
        print mx_download_url(url, 'pip')
        print mx_download_url(url, 'extended')

# Tests
#_test_mx_download_url()
#sys.exit(0)
        
# prerelease parsers used for conversion to PEP 386 format
PRERELEASE_RX = re.compile(
    '(?P<alpha>alpha|a)'
    '(?P<beta>beta|b)'
    '(?P<rc>rc|rc|c)'
    '(?P<dev>dev)'
    '[-_]+'
    '(?P<version>[0-9]+)'
    )

def mx_version(major=1, minor=0, patch=0, prerelease='', snapshot=None,
               sub_version=None, pep_compatible=False, separator='_'):

    """ Format the package version number.

        If sub_version is given as tuple of integers, it is appended
        to the major.minor.patch version string, with dots as
        delimiters.

        If prerelease is given, this is appended to the version
        string. The string should use the format
        '(alpha/beta/rc/dev)_123', e.g. 'beta_1'.

        If snapshot is true, the current date is added to the version
        string. snapshot defaults to true, if prerelease is set to
        'dev'.

        separator is used to separate prerelease and snapshot from the
        version number. Note that RPM doesn't like '-' in the version
        string. For this reason we use '_' as default.

        When using pep_compatible=True, the functions returns a
        version string that conforms to PEP 386. It's turned off by
        default for now to keep the function backwards compatible.

    """
    s = '%i.%i.%i' % (major, minor, patch)
    if sub_version:
        # Add sub_version tuple
        s += ''.join(['.%i' % x for x in sub_version])
    if prerelease:
        pr = PRERELEASE_RX.match(prerelease)
        if pep_compatible:
            if pr is None:
                raise TypeError('unsupported prerelease string: %r' %
                                prerelease)
            if pr.group('version'):
                pr_version = int(pr.group('version'))
            else:
                pr_version = 0
            if pr.group('alpha'):
                s += 'a%i' % pr_version
            elif pr.group('beta'):
                s += 'b%i' % pr_version
            elif pr.group('rc'):
                s += 'rc%i' % pr_version
            elif pr.group('dev'):
                snapshot = 1
        else:
            # Old style format
            s += '_' + prerelease
            if prerelease == 'dev' and snapshot is None:
                snapshot = 1
    if snapshot:
        import time
        now = time.gmtime(time.time())
        date = time.strftime('%Y%m%d', now)
        if pep_compatible:
            s += '.dev' + date
        else:
            # Old style format
            s += '_' + date
    return s

MX_VERSION_RE = re.compile('(\d+)\.(\d+)\.(\d+)')

def parse_mx_version(version):

    """ Convert a version string created with mx_version() back to
        its components.

        Returns a tuple (major, minor, patch, prerelease, snapshot).

        prerelease and snapshot are currently not supported and always
        set to '' and None.

        Raises a ValueError in case the version string cannot be
        parsed.

    """
    m = MX_VERSION_RE.match(version)
    if m is None:
        raise ValueError('incompatible version string format: %r' %
                         version)
    major, minor, patch = m.groups()
    major = int(major)
    minor = int(minor)
    patch = int(patch)
    prerelease = ''
    snapshot = None
    return major, minor, patch, prerelease, snapshot

def get_env_var(name, default=None, integer_value=0, yesno_value=0):

    value = os.environ.get(name, None)
    if value is None:
        return default

    # Try to convert to an integer, if possible
    if integer_value:
        try:
            return int(value)
        except ValueError:
            return default

    # Try to convert a yes/no value, if possible
    if yesno_value:
        value = value.strip().lower()
        if not value:
            return default
        if value[0] in ('y', '1'):
            return 1
        elif value == 'on':
            return 1
        else:
            return 0
        
    # Return the string value
    return value

def convert_to_platform_path(distutils_path):

    """ Convert a distutils Unix path distutils_path to the platform
        format.

    """
    if os.sep == '/':
        return distutils_path
    return os.sep.join(distutils_path.split('/'))

def convert_to_distutils_path(platform_path):

    """ Convert a platform path to the distutils Unix format.

    """
    if os.sep == '/':
        return platform_path
    return '/'.join(platform_path.split(os.sep))

def remove_path_prefix(pathname, prefix):

    """ Return a relative path by removing prefix from pathname.

        If pathname doesn't begin with prefix, no change is applied
        and pathname returned as-is.

    """
    prefix_len = len(prefix)
    if pathname[:prefix_len] != prefix:
        # pathname doesn't begin with prefix
        return pathname
    if prefix[-1] != os.sep:
        # Remove leading separator as well
        prefix_len += 1
    return pathname[prefix_len:]

def find_file(filename, paths, pattern=None):

    """ Look for a file in the directories defined in the list
        paths.

        If pattern is given, the found files are additionally checked
        to include the given RE search pattern. Pattern matching is
        done case-insensitive per default.

        Returns the directory where the file can be found or None in
        case it was not found.

        filename may include path components, e.g. if a particular
        file in a subdirectory is used as token to match the
        subdirectory.

    """
    if _debug:
        print 'looking for %s ...' % filename
        if pattern:
            print ' applying pattern check using %r' % pattern
    for dir in paths:
        pathname = os.path.join(dir, filename)
        if os.path.exists(pathname):
            if pattern:
                data = open(pathname, 'rb').read()
                if re.search(pattern, data, re.I) is None:
                    data = None
                    if _debug:
                        print ' %s: found, but not matched' % dir
                    continue
                data = None
                if _debug:
                    print ' %s: found and matched' % dir
            else:
                if _debug:
                    print ' %s: found' % dir
            return dir
        elif _debug:
            print ' %s: not found' % dir
    if _debug:
        print 'not found'
    return None

def is_python_package(path):

    """ Return 1/0 depending on whether path points to a Python
        package directory or not.

    """
    marker = '__init__' + os.extsep
    for filename in os.listdir(path):
        if filename.startswith(marker):
            return True
    return False

def python_module_name(path):

    """ Return the Python module name for the Python module path.

        Returns None if path does not point to a (potential) Python
        module.

    """
    for suffix in PY_SUFFIXES:
        if path.endswith(suffix):
            return os.path.basename(path[:-len(suffix)])
    return None

def find_python_modules(path):

    """ Find Python modules/packages available in path.

        Returns a dictionary mapping the Python module/package name
        (without extension) to either 'package' or 'module'.

    """
    d = {}
    for filename in os.listdir(path):
        pathname = os.path.join(path, filename)
        if os.path.isdir(pathname) and is_python_package(pathname):
            d[os.path.basename(filename)] = 'package'
        else:
            module_name = python_module_name(pathname)
            if module_name:
                d[module_name] = 'module'
    return d

def add_dir(dir, pathlist, index=-1):

    if dir not in pathlist and \
       os.path.isdir(dir):
        if index < 0:
            index = index + len(pathlist) + 1
        pathlist.insert(index, dir)

def py_unicode_build():

    """ Return the Python Unicode version.

        Possible values:
         'ucs2' - UCS2 build (standard Python source build)
         'ucs4' - UCS4 build (used on most recent Linux distros)
         ''     - No Unicode support

    """
    if sys.version[:3] >= '2.1':
        # UCS4 builds were introduced in Python 2.1; Note: RPM doesn't
        # like hyphens to be used in the Python version string which is
        # why we append the UCS information using an underscore.
        try:
            unichr(100000)
        except NameError:
            # No Unicode support
            return ''
        except ValueError:
            # UCS2 build (standard)
            return 'ucs2'
        else:
            # UCS4 build (most recent Linux distros)
            return 'ucs4'
    else:
        return ''


def py_version(unicode_aware=None, include_patchlevel=0):

    """ Return the Python version as short string.

        If unicode_aware is true (default on all platforms except
        win32, win16, os2 and dos), the function also tests whether a
        UCS2 or UCS4 built is running and modifies the version
        accordingly.

        If include_patchlevel is true (default is false), the patch
        level is also included in the version string.

    """
    if include_patchlevel:
        version = sys.version[:5]
    else:
        version = sys.version[:3]
    if unicode_aware is None:
        # Chose default for unicode_aware based on platform
        if sys.platform in ('win32', 'dos', 'win16', 'os2'):
            # These platforms always use UCS2 builds (at least for all
            # versions up until Python 2.6)
            unicode_aware = 0
        else:
            unicode_aware = 1
    if unicode_aware and version >= '2.1':
        # UCS4 builds were introduced in Python 2.1; Note: RPM doesn't
        # like hyphens to be used in the Python version string which is
        # why we append the UCS information using an underscore.
        try:
            unichr(100000)
        except ValueError:
            # UCS2 build (standard)
            version = version + '_ucs2'
        else:
            # UCS4 build (most recent Linux distros)
            version = version + '_ucs4'
    return version

def check_zope_product_version(version, version_txt):

    """ Check whether the version string version matches the
        version data in the Zope product version.txt file
        version_txt.

    """
    data = open(version_txt, 'r').read().strip()
    return data[-len(version):] == version

def verify_package_version(package, version):

    """ Check whether the Python package's __version__ matches
        the given version string.

        The first 3 version components must match,
        i.e. major.minor.patch. parse_mx_version() is used to extract
        this information from both the version string and the packages
        __version__ attribute.

        Raises a ValueError in case the versions do not match.

    """
    package_path = package.replace('.', os.sep)
    try:
        m = __import__(package_path, None, None, ['*'])
    except ImportError:
        raise ImportError('Cannot find %s package' % package)
    dist_version = parse_mx_version(version)
    package_version = parse_mx_version(m.__version__)
    if dist_version[:3] != package_version[:3]:
        raise ValueError('%s.__version__ mismatch: expected %s, found %s' %
                         (package, version, m.__version__))

# Keep the symbol around for backwards compatibility, but don't use it
# anymore.  See #943.
mx_customize_compiler = customize_compiler

compression_programs = {
    'gzip': ('.gz', '-f9'),
    'bzip2': ('.bz2', 'f9'),
    'compress': ('.Z', '-f'),
    }

def mx_make_tarball(base_name, base_dir, compression='gzip', verbose=0,
                    dry_run=0, owner=None, group=None,
                    tar_options='-h', **kws):

    # Much like archive_util.make_tarball, except that this version
    # dereferences symbolic links.
    tar_archive = base_name + '.tar'

    # Create the directory for the archive
    mkpath(os.path.dirname(tar_archive), dry_run=dry_run)

    # Create the archive
    if owner:
        tar_options += ' --owner="%s"' % owner
    if group:
        tar_options += ' --group="%s"' % group
    cmd = ['tar', '-c', tar_options, '-f', tar_archive, base_dir]
    spawn(cmd, verbose=verbose, dry_run=dry_run)

    # Compress if that's needed
    if compression:
        try:
            ext, options = compression_programs[compression]
        except KeyError:
            raise ValueError('unknown compression program: %s' % compression)
        cmd = [compression, options, tar_archive]
        spawn(cmd, verbose=verbose, dry_run=dry_run)
        tar_archive = tar_archive + ext
        
    return tar_archive

# Register our version of make_tarball()
register_archive_formats = {
    'gztar': (mx_make_tarball, [('compression', 'gzip')], 'gzipped tar-file'),
    'bztar': (mx_make_tarball, [('compression', 'bzip2')], 'bzip2ed tar-file'),
    'ztar':  (mx_make_tarball, [('compression', 'compress')], 'compressed tar file'),
    'tar':   (mx_make_tarball, [('compression', None)], 'tar file'),
    }
if not hasattr(shutil, 'register_format'):
    # In Python <2.7, 3.0 and 3.1, we have to register straight with
    # the distutils ARCHIVE_FORMATS dictionary
    distutils.archive_util.ARCHIVE_FORMATS.update(register_archive_formats)
else:
    # Python 2.7+ and 3.2+ use the new shutil archive functions instead
    # of the ones from distutils, so register our archives there
    for archive_name, archive_params in register_archive_formats.items():
        shutil.register_format(archive_name, *archive_params)

def build_path(dirs):

    """ Builds a path list from a list of directories/paths.

        The dirs list may contain shell variable references and user
        dir references. These will get expanded
        automatically. Non-existing shell variables are replaced with
        an empty string. Path entries will get expanded to single
        directory entries.  Empty string entries are removed from the
        list.

    """
    try:
        expandvars = os.path.expandvars
    except AttributeError:
        expandvars = None
    try:
        expanduser = os.path.expanduser
    except AttributeError:
        expanduser = None
    path = []
    for i in range(len(dirs)):
        dir = dirs[i]
        if expanduser is not None:
            dir = expanduser(dir)
        if expandvars is not None:
            dir = expandvars(dir)
            if '$' in dir:
                dir = ''.join(re.split(r'\$\w+|\{[^}]*\}', dir))
        dir = dir.strip()
        if os.pathsep in dir:
            path.extend(dir.split(os.pathsep))
        elif dir:
            path.append(dir)
        # empty entries are omitted
    return path

def verify_path(path):

    """ Verify the directories in path for existence and their
        directory nature.

        Also removes duplicates from the list.

    """
    d = {}
    l = []
    for dir in path:
        if os.path.exists(dir) and \
           os.path.isdir(dir):
            if not d.has_key(dir):
                d[dir] = 1
                l.append(dir)
    path[:] = l

def get_msvc_paths():

    """ Return a tuple (libpath, inclpath) defining the search
        paths for library files and include files that the MS VC++
        compiler uses per default.

        Both entries are lists of directories.

        Only available on Windows platforms with installed compiler.

    """
    if python_version >= '2.6':
        # Python 2.6 distutils

        # If possible, assume that the environment is already
        # properly setup and read the setting from there - this is
        # important since we could be cross-compiling
        if os.environ.has_key('lib') and os.environ.has_key('include'):
            return (os.environ['lib'].split(os.pathsep),
                    os.environ['include'].split(os.pathsep))
        else:
            # Use the old compiler code
            from distutils.msvccompiler import OldMSVCCompiler
            try:
                msvccompiler = OldMSVCCompiler()
                inclpath = msvccompiler.get_msvc_paths('include')
                libpath = msvccompiler.get_msvc_paths('library')
            except Exception, why:
                log.error('*** Problem: %s' % why)
                import traceback
                traceback.print_exc()
                libpath = []
                inclpath = []
            msvccompiler = None

    elif python_version >= '2.3':
        # Python 2.3 - 2.5 distutils
        try:
            msvccompiler = MSVCCompiler()
            inclpath = msvccompiler.get_msvc_paths('include')
            libpath = msvccompiler.get_msvc_paths('library')
        except Exception, why:
            log.error('*** Problem: %s' % why)
            import traceback
            traceback.print_exc()
            libpath = []
            inclpath = []
        msvccompiler = None

    else:
        # distutils versions prior to the one that came with Python 2.3
        from distutils.msvccompiler import get_devstudio_versions, get_msvc_paths
        msvc_versions = get_devstudio_versions()
        if msvc_versions:
            msvc_version = msvc_versions[0] # choose most recent one
            inclpath = get_msvc_paths('include', msvc_version)
            libpath = get_msvc_paths('lib', msvc_version)
        else:
            libpath = []
            inclpath = []

    return libpath, inclpath

#
# Search paths
#
        
# Standard system directories which are automatically scanned by the
# compiler and linker for include files and libraries. LIB and INCLUDE
# are environment variables used on Windows platforms, other platforms
# may have different names.
STDLIBPATH = build_path(['/usr/lib', '/opt/lib', '$LIB'])
STDINCLPATH = build_path(['/usr/include', '/opt/include', '$INCLUDE'])

# Add additional dirs from Windows registry if available
if sys.platform[:3] == 'win':
    libpath, inclpath = get_msvc_paths()
    STDLIBPATH.extend(libpath)
    STDINCLPATH.extend(inclpath)

# Default paths for additional library and include file search (in
# addition to the standard system directories above); these are always
# added to the compile and link commands by mxSetup per default.
LIBPATH = build_path(['/usr/local/lib',
                      '/opt/local/lib',
                      os.path.join(sys.prefix, 'lib')])
INCLPATH = build_path(['/usr/local/include',
                       '/opt/local/include',
                       os.path.join(sys.prefix, 'include')])

# Add 32- or 64-bit dirs if needed by the Python version
if sys.maxint > 2147483647L:
    # 64-bit build
    STDLIBPATH.extend(['/usr/lib64', '/opt/lib64'])
    LIBPATH.extend(['/usr/local/lib64', '/opt/local/lib64'])
else:
    # 32-bit build
    STDLIBPATH.extend(['/usr/lib32', '/opt/lib32'])
    LIBPATH.extend(['/usr/local/lib32', '/opt/local/lib32'])

# Additional paths to scan in order to find third party libs and
# headers; these are used by mx_autoconf.find_*_file() APIs.
FINDLIBPATH = build_path([])
FINDINCLPATH = build_path([])

verify_path(STDLIBPATH)
verify_path(STDINCLPATH)
verify_path(LIBPATH)
verify_path(INCLPATH)
verify_path(FINDLIBPATH)
verify_path(FINDINCLPATH)

if 0:
    # Work-around for quirk on Solaris which happens to be a common
    # problem when compiling things with GCC: there's a non-GCC stdarg.h
    # header file in /usr/include which gets picked up by GCC instead of
    # its own compiler specific one, so we remove /usr/include from
    # INCLPATH in that situation.
    if sys.platform == 'sunos5' and \
       sys.version.find('GCC') >= 0:
        if os.path.exists('/usr/include/stdarg.h'):
            INCLPATH.remove('/usr/include')

#
# File extensions
#

# Library types to search for (see distutils.ccompiler)
if sys.platform == 'darwin':
    # Mac OS X uses .dylibs in addition to .so files, so we need to
    # search for those as well
    #
    # Note that only the distutils unixcompiler supports searching for
    # dylib, other compiler classes will simply exist with an
    # AttributeError
    LIB_TYPES = ('dylib', 'shared', 'static')
    
else:
    # These types are supported by all compiler classes
    LIB_TYPES = ('shared', 'static')


if _debug > 1:
    # Note that printing these lines to stdout can cause scripts that
    # use mxSetup for extracting information from the setup module to
    # fail, since they don't expect the extra output. This is why we
    # only show this information for higher _debug levels.
    print 'mxSetup will be using these search paths:'
    print ' std lib path:', STDLIBPATH
    print ' std include path:', STDINCLPATH
    print ' additional lib path:', LIBPATH
    print ' additional include path:', INCLPATH
    print ' additional autoconf lib path:', FINDLIBPATH
    print ' additional autoconf include path:', FINDINCLPATH
    print ' library types:', LIB_TYPES
    print ' Python include path: %r' % get_python_include_dir()

#
# Mixin helpers
#

class CompilerSupportMixin:

    """ Compiler support mixin which makes sure that the .compiler
        attribute is properly setup.
    
    """
    # Internal flag
    prepared_compiler = 0

    def prepare_compiler(self):

        # Setup .compiler instance
        compiler = self._get_compiler_object()
        if compiler is None:
            if hasattr(self, '_check_compiler'):
                # The config command has this method to setup the
                # compiler
                self._check_compiler()
            else:
                raise CCompilerError('no C compiler setup; cannot continue')
            compiler = self._get_compiler_object()
            
        elif self.prepared_compiler:
            # Return the already prepared compiler
            return compiler
        
        # Work around a bug in distutils <= 1.0.3
        if compiler.exe_extension is None:
            compiler.exe_extension = ''

        # Make sure we have a typical setup for directory
        # searches
        for dir in LIBPATH:
            add_dir(dir, compiler.library_dirs)
        for dir in INCLPATH:
            add_dir(dir, compiler.include_dirs)

        # Add the Python include dir
        add_dir(get_python_include_dir(), compiler.include_dirs)

        # Customize the compiler according to system settings
        customize_compiler(compiler)

        log.info('configured compiler')
        self.prepared_compiler = 1

        return compiler

    def reset_compiler(self):

        """ Reset a possibly already prepared compiler.

            The compiler will have to be prepared again using
            .prepared_compiler().

        """
        self._set_compiler_object(None)
        self.prepared_compiler = 0

    def _get_compiler_object(self):

        """ Get the command's compiler object.

        """
        # See the change and discussion for
        # http://bugs.python.org/issue6377, new in Python 2.7
        # The change was later reverted, so this probably never
        # triggers. See http://bugs.python.org/issue13994
        if hasattr(self, 'compiler_obj'):
            return self.compiler_obj
        else:
            return self.compiler

    def _set_compiler_object(self, compiler):

        """ Set the command's compiler object.

        """
        # See the change and discussion for
        # http://bugs.python.org/issue6377, new in Python 2.7
        # The change was later reverted, so this probably never
        # triggers. See http://bugs.python.org/issue13994
        if hasattr(self, 'compiler_obj'):
            self.compiler_obj = compiler
        else:
            self.compiler = compiler

#
# mx Auto-Configuration command
#

class mx_autoconf(CompilerSupportMixin,
                  config):

    """ Auto-configuration class which adds some extra configuration
        settings to the packages.

    """
    # Command description
    description = "auto-configuration build step (for internal use only)"

    # Command line options
    user_options = config.user_options + [
        ('enable-debugging', None,
         'compile with debugging support (env var: MX_ENABLE_DEBUGGING)'),
        ('defines=', None,
         'define C macros (example: A=1,B=2,C,D)'),
        ('undefs=', None,
         'define C macros (example: A,B,C)'),
        ]

    # User option defaults
    enable_debugging = 0
    defines = None
    undefs = None

    # C APIs to check: (C API name, list of header files to include)
    api_checks = (
        ('strftime', ['time.h']),
        ('strptime', ['time.h']),
        ('timegm', ['time.h']),
        ('clock_gettime', ['time.h']),
        ('clock_getres', ['time.h']),
        #('this_always_fails', []), # For testing the detection mechanism
        )

    def initialize_options(self):

        config.initialize_options(self)
        self.noisy = 0
        self.dump_source = 0

        if not self.enable_debugging:
            # Enable debugging for dev snapshots
            version = self.distribution.metadata.get_version()
            if has_substring('dev', version):
                self.enable_debugging = 1
                log.warn('debugging enabled for development snapshots')

        if not self.enable_debugging:
            # Enable debugging via env variable MX_ENABLE_DEBUGGING
            if get_env_var('MX_ENABLE_DEBUGGING', default=0, yesno_value=1):
                self.enable_debugging = 1
                log.warn('debugging enabled via '
                         'MX_ENABLE_DEBUGGING environment variable')

    def finalize_options(self):

        config.finalize_options(self)
        
        if self.defines:
            defines = []
            for defstr in self.defines.split(','):
                defstr = defstr.strip()
                if '=' in defstr:
                    defname, defvalue = defstr.split('=')
                    defname = defname.strip()
                    defvalue = defvalue.strip()
                else:
                    defname = defstr
                    defvalue = '1'
                defines.append((defname, defvalue))
            self.defines = defines
        else:
            self.defines = []

        if self.undefs:
            undefs = []
            for undefstr in self.undefs.split(','):
                undefname = undefstr.strip()
                undefs.append(undefname)
            self.undefs = undefs
        else:
            self.undefs = []

    def get_outputs(self):

        """ We don't generate any output.

        """
        return []

    def run(self):

        # Setup compiler
        compiler = self.prepare_compiler()        

        # Check compiler setup
        log.info('checking compiler setup')
        if not self.compiler_available():
            if sys.platform == 'darwin':
                # On Mac OS X, Apple removed the GCC compiler from
                # Xcode 4.1, but the Python installers are still
                # compiled with GCC, so distutils will default to
                # looking for GCC (see Python issue #13590). We'll try
                # clang as fallback solution.
                cc, cxx, ldshared = get_config_vars('CC', 'CXX', 'LDSHARED')
                log.info('compiler problem: "%s" not available, trying '
                         '"clang" instead' % cc)
                if 'CC' not in os.environ:
                    os.environ['CC'] = 'clang'
                if 'CXX' not in os.environ:
                    os.environ['CXX'] = 'clang'
                if 'LDSHARED' not in os.environ:
                    if ldshared.startswith(cc):
                        ldshared = 'clang ' + ldshared[len(cc):]
                    os.environ['LDSHARED'] = ldshared
                self.reset_compiler()
                compiler = self.prepare_compiler()
                if self.compiler_available():
                    log.info('using "clang" instead of "%s"' % cc)
                else:
                    log.info('no working compiler found; '
                             'please install Xcode first')
                    raise CCompilerError('no compiler available')
            else:
                log.error('compiler setup does not work or no compiler found; '
                          'try adjusting the CC/LDSHARED environemnt variables '
                          'to point to the installed compiler')
                raise CCompilerError('no compiler available')
        log.info('compiler setup works')

        # Add some static #defines which should not hurt
        compiler.define_macro('_GNU_SOURCE', '1')

        # Parse [py]config.h
        config_h = get_config_h_filename()
        try:
            configfile = open(config_h)
        except IOError,why:
            log.warn('could not open %s file' % config_h)
            configuration = {}
        else:
            configuration = parse_config_h(configfile)
            configfile.close()

        # Tweak configuration a little for some platforms
        if sys.platform[:5] == 'win32':
            configuration['HAVE_STRFTIME'] = 1

        # Build lists of #defines and #undefs
        define = []
        undef = []

        # Check APIs
        for apiname, includefiles in self.api_checks:
            macro_name = 'HAVE_' + apiname.upper()
            if not configuration.has_key(macro_name):
                log.info('checking for availability of %s() '
                         '(errors from this can safely be ignored)' % apiname)
                if self.check_function(apiname, includefiles):
                    log.info('%s() is available on this platform' %
                             apiname)
                    define.append((macro_name, '1'))
                else:
                    log.info('%s() is not available on this platform' %
                             apiname)
                    undef.append(macro_name)

        # Compiler tests
        if not configuration.has_key('BAD_STATIC_FORWARD'):
            log.info('checking compiler for bad static forward handling '
                     '(errors from this can safely be ignored)')
            if self.check_bad_staticforward():
                log.info('compiler has problems with static forwards '
                         '- enabling work-around')
                define.append(('BAD_STATIC_FORWARD', '1'))

        # Enable debugging support
        if self.enable_debugging:
            log.info('enabling mx debug support')
            define.append(('MAL_DEBUG', None))

        # Add extra #defines and #undefs
        if self.defines:
            define.extend(self.defines)
        if self.undefs:
            undef.extend(self.undefs)

        log.info('macros to define: %s' % define)
        log.info('macros to undefine: %s' % undef)

        # Reinitialize build_ext command with extra defines
        build_ext = self.distribution.reinitialize_command('build_ext')
        build_ext.ensure_finalized()
        # We set these here, since distutils 1.0.2 introduced a
        # new incompatible way to process .define and .undef
        if build_ext.define:
            #print repr(build_ext.define)
            if type(build_ext.define) is types.StringType:
                # distutils < 1.0.2 needs this:
                l = build_ext.define.split(',')
                build_ext.define = map(lambda symbol: (symbol, '1'), l)
            build_ext.define = build_ext.define + define
        else:
            build_ext.define = define
        if build_ext.undef:
            #print repr(build_ext.undef)
            if type(build_ext.undef) is types.StringType:
                # distutils < 1.0.2 needs this:
                build_ext.undef = build_ext.undef.split(',')
            build_ext.undef = build_ext.undef + undef
        else:
            build_ext.undef = undef
        log.debug('updated build_ext with autoconf setup')

    def compiler_available(self):

        """ Check whether the compiler works.

            Return 1/0 depending on whether the compiler can produce
            code or not.
        
        """
        body = "int main (void) { return 0; }"
        return self.check_compiler(body)

    def check_compiler(self, sourcecode, headers=None, include_dirs=None,
                       libraries=None, library_dirs=None):

        """ Check whether sourcecode compiles and links with the current
            compiler and link environment.

            For documentation of the other arguments see the base
            class' .try_link().
        
        """
        self.prepare_compiler()
        return self.try_link(sourcecode, headers, include_dirs,
                             libraries, library_dirs)

    def check_bad_staticforward(self):

        """ Check whether the compiler does not supports forward declaring
            static arrays.

            For documentation of the other arguments see the base
            class' .try_link().
        
        """
        body = """
        typedef struct _mxstruct {int a; int b;} mxstruct;
        staticforward mxstruct mxarray[];
        statichere mxstruct mxarray[] = {{0,2},{3,4},};
        int main(void) {return mxarray[0].a;}
        """
        self.prepare_compiler()
        return not self.try_compile(body,
                                    headers=('Python.h',),
                                    include_dirs=[get_python_include_dir()])

    def check_function(self, function, headers=None, include_dirs=None,
                       libraries=None, library_dirs=None,
                       prototype=0, call=0):

        """ Check whether function is available in the given
            compile and link environment.

            If prototype is true, a function prototype is included in
            the test. If call is true, a function call is generated
            (rather than just a reference of the function symbol).

            For documentation of the other arguments see the base
            class' .try_link().
        
        """
        body = []
        if prototype:
            body.append("int %s (void);" % function)
        body.append("int main (void) {\n"
                    "  void *ptr = 0; ")
        if call:
            body.append("  %s();" % function)
        else:
            body.append("  ptr = &%s;" % function)
        body.append("return 0; }")
        body = "\n".join(body) + "\n"
        return self.check_compiler(body, headers, include_dirs,
                                   libraries, library_dirs)

    def check_library(self, library, library_dirs=None,
                      headers=None, include_dirs=None, other_libraries=[]):

        """ Check whether we can link against the given library.

            For documentation of the other arguments see the base
            class' .try_link().
        
        """
        body = "int main (void) { return 0; }"
        return self.check_compiler(body, headers, include_dirs,
                                   [library]+other_libraries, library_dirs)

    def find_include_file(self, filename, paths, pattern=None):

        """ Find an include file of the given name.

            Returns a tuple (directory, filename) or (None, None) in
            case no library can be found.

            The search path is determined by the paths parameter, the
            compiler's .include_dirs attribute and the STDINCLPATH and
            FINDINCLPATH globals. The search is done in this order.

        """
        compiler = self.prepare_compiler()
        paths = (paths
                 + compiler.include_dirs
                 + STDINCLPATH
                 + FINDINCLPATH)
        verify_path(paths)
        if _debug:
            print 'INCLPATH', paths
        dir = find_file(filename, paths, pattern)
        if dir is None:
            return (None, None)
        return (dir, os.path.join(dir, filename))

    def find_library_file(self, libname, paths, pattern=None,
                          lib_types=LIB_TYPES):

        """ Find a library of the given name.

            Returns a tuple (directory, filename) or (None, None) in
            case no library can be found.

            The search path is determined by the paths parameter, the
            compiler's .library_dirs attribute and the STDLIBPATH and
            FINDLIBPATH globals. The search is done in this order.

            Shared libraries are prefered over static ones if both
            types are given in lib_types.

        """
        compiler = self.prepare_compiler()
        paths = (paths
                 + compiler.library_dirs
                 + STDLIBPATH
                 + FINDLIBPATH)
        verify_path(paths)
        if _debug:
            print 'LIBPATH: %r' % paths
            print 'Library types: %r' % lib_types

        # Try to first find a shared library to use and revert
        # to a static one, if no shared lib can be found
        for lib_type in lib_types:
            filename = compiler.library_filename(libname,
                                                 lib_type=lib_type)
            if _debug:
                print 'looking for library file %s' % filename
            dir = find_file(filename, paths, pattern)
            if dir is not None:
                return (dir, os.path.join(dir, filename))
            
        return (None, None)

#
# mx MSVC Compiler extension
#
# We want some extra options for the MSVCCompiler, so we add them
# here. This is an awful hack, but there seems to be no other way to
# subclass a standard distutils C compiler class...

if python_version < '2.4':
    # VC6
    MSVC_COMPILER_FLAGS = ['/O2', '/Gf', '/GB', '/GD', '/Ob2']
elif python_version < '2.6':
    # VC7.1
    MSVC_COMPILER_FLAGS = ['/O2', '/GF', '/GB', '/Ob2']
else:
    # VC9
    MSVC_COMPILER_FLAGS = ['/O2', '/GF', '/Ob2']

if hasattr(MSVCCompiler, 'initialize'):
    # distutils 2.5.0 separates the initialization of the
    # .compile_options out into a new method .initialize()

    # remember old _initialize
    old_MSVCCompiler_initialize = MSVCCompiler.initialize

    def mx_msvccompiler_initialize(self, *args, **kws):

        apply(old_MSVCCompiler_initialize, (self,) + args, kws)

        # Add our extra options
        self.compile_options.extend(MSVC_COMPILER_FLAGS)

    # "Install" new initialize
    MSVCCompiler.initialize = mx_msvccompiler_initialize

else:
    # distutils prior to 2.5.0 only allow to hook into the .__init__()
    # method

    # remember old __init__
    old_MSVCCompiler__init__ = MSVCCompiler.__init__

    def mx_msvccompiler__init__(self, *args, **kws):

        apply(old_MSVCCompiler__init__, (self,) + args, kws)

        # distutils 2.5.0 separates the initialization of the
        # .compile_options out into a new method
        if hasattr(self, 'initialized') and not self.initialized:
            self.initialize()

        # Add out extra options
        self.compile_options.extend(MSVC_COMPILER_FLAGS)

    # "Install" new __init__
    MSVCCompiler.__init__ = mx_msvccompiler__init__

#
# mx Distribution class
#

class mx_Distribution(Distribution):

    """ Distribution class which knows about our distutils extensions.
        
    """
    # List of UnixLibrary instances
    unixlibs = None

    # Option to override the package version number
    set_version = None

    # List of setuptools namespace package names
    namespace_packages = None

    # List of setuptools dependency links
    dependency_links = None

    # Add classifiers dummy option if needed
    display_options = Distribution.display_options[:]
    display_option_names = Distribution.display_option_names[:]
    if 'classifiers' not in display_options:
        display_options = display_options + [
            ('classifiers', None,
             "print the list of classifiers (not yet supported)"),
        ]
        display_option_names = display_option_names + [
            'classifiers'
            ]

    # Add set-version option
    global_options = Distribution.global_options[:]
    global_options = global_options + [
        ('set-version=', None, "override the package version number"),
        ]

    def finalize_options(self):

        if self.namespace_packages is None:
            self.namespace_packages = []
        if self.dependency_links is None:
            self.dependency_links = []

        # Call base method
        Distribution.finalize_options(self)

    def parse_command_line(self):

        if not Distribution.parse_command_line(self):
            return

        # Override the version information from the package with a
        # command-line given version string
        if self.set_version is not None:
            self.metadata.version = self.set_version
            self.version = self.set_version

        return 1

    def has_unixlibs(self):
        return self.unixlibs and len(self.unixlibs) > 0

    def get_namespace_packages(self):
        return self.namespace_packages or []

    def get_dependency_links(self):
        return self.dependency_links or []

#
# mx Extension class
#

class mx_Extension(Extension):

    """ Extension class which allows specifying whether the extension
        is required to build or optional.
        
    """
    # Is this Extension required to build or can we issue a Warning in
    # case it fails to build and continue with the remaining build
    # process ?
    required = 1

    # List of optional libaries (libname, list of header files to
    # check) to include in the link step; the availability of these is
    # tested prior to compiling the extension. If found, the symbol
    # HAVE_<upper(libname)>_LIB is defined and the library included in
    # the list of libraries to link against.
    optional_libraries = ()

    # List of needed include files in form of tuples (filename,
    # [dir1, dir2,...], pattern); see mx_autoconf.find_file()
    # for details
    needed_includes = ()

    # List of needed include files in form of tuples (libname,
    # [dir1, dir2,...], pattern); see mx_autoconf.find_library_file()
    # for details
    needed_libraries = ()

    # Include the found library files in the extension output ?  This
    # causes the files to be copied into the same location as the
    # extension itself.
    include_needed_libraries = 0

    # Library types to check (for needed libraries)
    lib_types = LIB_TYPES

    # Data files needed by this extension (these are only
    # installed if building the extension succeeded)
    data_files = ()

    # Python packages needed by this extension (these are only
    # installed if building the extension succeeded)
    packages = ()

    # Building success marker
    successfully_built = 0

    # NOTE: If you add new features to this class, also adjust
    # rebase_extensions()

    def __init__(self, *args, **kws):
        for attr in ('required',
                     'lib_types',
                     'optional_libraries',
                     'needed_includes',
                     'needed_libraries',
                     'include_needed_libraries',
                     'data_files',
                     'packages'):
            if kws.has_key(attr):
                setattr(self, attr, kws[attr])
                del kws[attr]
            else:
                value = getattr(self, attr)
                if type(value) == type(()):
                    setattr(self, attr, list(value))
        apply(Extension.__init__, (self,) + args, kws)

#
# mx Build command
#

class mx_build(build):

    """ build command which knows about our distutils extensions.

        This build command builds extensions in properly separated
        directories (which includes building different Unicode
        variants in different directories).
        
    """
    # Skip the build process ?
    skip = None

    # Assume prebuilt archive ?
    prebuilt = None
   
    user_options = build.user_options + [
            ('skip', None,
             'skip build and reuse the existing build files'),
            ('prebuilt', None,
             'assume we have a prebuilt archive (even without %s file)' %
             PREBUILT_MARKER),
            ]

    def finalize_options(self):

        # Make sure different Python versions are built in separate
        # directories
        python_platform = '.%s-%s' % (mx_get_platform(), py_version())
        if self.build_platlib is None:
            self.build_platlib = os.path.join(
                self.build_base,
                'lib' + python_platform)
        if self.build_purelib is None:
            self.build_purelib = os.path.join(
                self.build_base,
                'lib.' + py_version(unicode_aware=0))
        if self.build_temp is None:
            self.build_temp = os.path.join(
                self.build_base,
                'temp' + python_platform)

        # Call the base method
        build.finalize_options(self)

        if self.skip is None:
            self.skip = 0
            
        # Handle prebuilt archives
        if self.prebuilt is None:
            if os.path.exists(PREBUILT_MARKER):
                self.prebuilt = 1
            else:
                self.prebuilt = 0

        if self.prebuilt:
            if not self.have_build_pickle():
                # Either the build pickle is missing or not compatible
                # with the currently running Python interpreter.  Read
                # setup information from the build pickle; the path to
                # this file is stored in the PREBUILT_MARKER file.
                if os.path.exists(PREBUILT_MARKER):
                    build_pickle_pathname = (
                        open(PREBUILT_MARKER, 'rb').read().strip())
                    build_pickle = self.read_build_pickle(
                        build_pickle_pathname)
                    mxSetup = build_pickle.get('mxSetup', {})
                else:
                    mxSetup = {}
                    
                print """
--------------------------------------------------------------------

ERROR: Cannot find the build information needed for your platform.
                
Please check that you have downloaded the right prebuilt archive for
your platform and Python version.

Product name:        %s
Product version:     %s
    
Your Python installation uses these settings:

    Python version:  %s
    Platform:        %s

The prebuilt archive was built for:

    Python version:  %s
    Platform:        %s

--------------------------------------------------------------------
                """.strip() % (
                self.distribution.metadata.get_name(),
                self.distribution.metadata.get_version(),
                py_version(unicode_aware=1),
                mx_get_platform(),
                mxSetup.get('py_version', 'unknown'),
                mxSetup.get('get_platform', 'unknown'))
                sys.exit(1)
            if self.force:
                log.info('prebuilt archive found: ignoring the --force option')
                self.force = 0
                
            # Override settings with data from a possibly existing
            # build pickle
            log.info('prebuilt archive found: skipping the build process and '
                     'reusing the existing build files and data')
            self.load_build_pickle()

        # Use the build pickle, in case we are supposed to skip the
        # build
        if self.skip and self.have_build_pickle():
            log.info('skipping the build process and '
                     'reusing the existing build files and data')
            self.load_build_pickle()

    def get_outputs(self):

        """ Collect the outputs of all sub-commands (this knows about
            the extra commands we added).

            This is needed by mx_bdist_prebuilt and mx_uninstall.

        """
        outputs = {}
        for sub_command in self.get_sub_commands():
            cmd = self.get_finalized_command(sub_command)
            if not hasattr(cmd, 'get_outputs'):
                log.error('problem: missing .get_outputs() ... %r' % cmd)
                raise ValueError('missing .get_outputs() implementation '
                                 'for command %r' % cmd)
            for filename in cmd.get_outputs():
                outputs[filename] = 1

        # Add pickle, if available
        pickle_filename = self.get_build_pickle_pathname()
        if os.path.exists(pickle_filename):
            if _debug:
                print 'added pickle:', pickle_filename
            outputs[pickle_filename] = 1

        # Return a sorted list
        outputs = outputs.keys()
        outputs.sort()
        return outputs

    def pure_python_build(self):

        """ Return 1/0 depending on whether this is a pure Python
            build or not.

            Pure Python builds do not include extensions.

        """
        return not self.distribution.ext_modules

    def get_build_pickle_pathname(self):

        """ Return the path name for the build pickle file.

            Note that the target system loading these pickles may well
            return different values for get_platform() than the system
            used to compile the build.

            We therefore do not include the platform in the pathname,
            only the Python version (to prevent obvious user errors
            related to downloading the wrong prebuilt archive for
            their Python version).

            For pure Python distributions (ones without extensions),
            we also don't include the Unicode tag in the pickle name.

        """
        unicode_aware = not self.pure_python_build()
        return os.path.join(
            self.build_base,
            'build-py%s.pck' % (py_version(unicode_aware=unicode_aware)))

    def write_build_pickle(self, pathname=None):

        """ Write the current state of the distribution, the
            build command and all sub-commands to a Python
            pickle in the build directory.

            If pathname is not given, .get_build_pickle_pathname() is
            used as default.

        """
        if pathname is None:
            pathname = self.get_build_pickle_pathname()

        # Prepare the sub commands for pickle'ing
        self.get_outputs()

        # Remove data that would cause conflicts when restoring the
        # build pickle
        data = self.__dict__.copy()
        if data.has_key('distribution'):
            del data['distribution']
        if data.has_key('compiler'):
            del data['compiler']
        state = {'build': data}
        for sub_command, needed in self.sub_commands:
            cmd = self.distribution.get_command_obj(sub_command)
            data = cmd.__dict__.copy()
            if data.has_key('distribution'):
                del data['distribution']
            if data.has_key('compiler'):
                del data['compiler']
            if data.has_key('extensions'):
                del data['extensions']
            if data.has_key('autoconf'):
                del data['autoconf']
            state[sub_command] = data
        data = {'have_run': self.distribution.have_run,
                'data_files': self.distribution.data_files,
                }
        state['distribution'] = data
        if 0:
            data = self.distribution.__dict__.copy()
            if data.has_key('distribution'):
                del data['distribution']
            if data.has_key('metadata'):
                del data['metadata']
            if data.has_key('ext_modules'):
                del data['ext_modules']
            if data.has_key('command_obj'):
                del data['command_obj']
            if data.has_key('cmdclass'):
                del data['cmdclass']
            for key, value in data.items():
                if type(value) is type(self.distribution.get_url):
                    # Bound method
                    del data[key]
                elif type(value) is type(self.distribution):
                    # Instance
                    del data[key]
            state['distribution'] = data


        # Save additional meta-data
        pure_python_build = self.pure_python_build()
        unicode_aware = not pure_python_build
        state['mxSetup'] = {
            '__version__': __version__,
            'unicode_aware': unicode_aware, 
            'py_version': py_version(unicode_aware=unicode_aware),
            'sys_platform': sys.platform,
            'get_name': self.distribution.metadata.get_name(),
            'get_version': self.distribution.metadata.get_version(),
            'get_platform': mx_get_platform(),
            'pure_python_build': pure_python_build,
            }

        # Save pickle
        if _debug:
            print 'saving build pickle:', repr(state)
        pickle_file = open(self.get_build_pickle_pathname(),
                           'wb')
        cPickle.dump(state, pickle_file)
        pickle_file.close()

    def have_build_pickle(self, pathname=None,
                          ignore_distutils_platform=True,
                          ignore_distribution_version=True,
                          ignore_sys_platform=None):

        """ Return 1/0 depending on whether there is a build pickle
            that could be used or not.

            If pathname is not given, .get_build_pickle_pathname() is
            used as default.

            If ignore_platform is set (default), the platform
            information stored in the pickle is ignored in the check.
            This is useful, since the value of the build system may
            differ from the target system (e.g. for fat builds on Mac
            OS X that get installed on Intel Macs).

            If ignore_distribution_version is set (default), the
            distribution version information in the pickle is ignored.
            This is useful for cases where the version determined at
            build time can be different than at installation time,
            e.g. due to a timestamp being created dynamically and
            added to the version.

            If ignore_sys_platform is set (default is false for builds
            with C extensions and true for pure Python builds), the
            sys.platform version information in the pickle is ignored.

        """
        if pathname is None:
            pathname = self.get_build_pickle_pathname()
        try:
            pickle_file = open(pathname, 'rb')
        except IOError:
            log.info('no build data file %r found' % pathname)
            return 0
        state = cPickle.load(pickle_file)
        pickle_file.close()

        # Check whether this is a valid build file for this Python
        # version
        mxSetup = state.get('mxSetup', None)
        if mxSetup is None:
            return 0
        unicode_aware = mxSetup.get('unicode_aware', 1)
        pure_python_build = mxSetup.get('pure_python_build', 0)
        if ignore_sys_platform is None:
            if pure_python_build:
                if mxSetup['sys_platform'].startswith('win'):
                    # Prebuilt archives built on win32 can only be
                    # installed there, since the os.sep does not
                    # correspond to the distutils standard of '/'.
                    ignore_sys_platform = False
                else:
                    ignore_sys_platform = True
        if mxSetup['__version__'] != __version__:
            log.info('build data file %r found, '
                     'but mxSetup version does not match; not using it' %
                     pathname)
            return 0
        if mxSetup['py_version'] != py_version(unicode_aware=unicode_aware):
            log.info('build data file %r found, '
                     'but Python version does not match; not using it' %
                     pathname)
            return 0
        if ((not ignore_sys_platform) and
            mxSetup['sys_platform'] != sys.platform):
            log.info('build data file %r found, '
                     'but sys.platform does not match; not using it' %
                     pathname)
            return 0
        if mxSetup['get_name'] != self.distribution.metadata.get_name():
            log.info('build data file %r found, '
                     'but distribution name does not match; not using it' %
                     pathname)
            return 0
        if ((not ignore_distribution_version) and
            mxSetup['get_version'] != self.distribution.metadata.get_version()):
            log.info('build data file %r found, '
                     'but distribution version does not match; not using it' %
                     pathname)
            return 0
        if ((not ignore_distutils_platform) and
            mxSetup['get_platform'] != mx_get_platform()):
            log.info('build data file %r found, '
                     'but distutils platform does not match; not using it' %
                     pathname)
            return 0

        log.info('found usable build data file %r' % pathname)
        return 1

    def read_build_pickle(self, pathname=None):

        """ Read the pickle written by the .write_build_pickle() method.

            If pathname is not given, .get_build_pickle_pathname() is
            used as default.

        """
        if pathname is None:
            pathname = self.get_build_pickle_pathname()
        pickle_file = open(pathname, 'rb')
        state = cPickle.load(pickle_file)
        pickle_file.close()
        if _debug:
            print 'read build pickle:'
            import pprint
            pprint.pprint(state)
        return state

    def load_build_pickle(self):

        """ Restore the state written by the .write_build_pickle() method.

        """
        # Read pickle file
        state = self.read_build_pickle()

        # Adjust distutils platform string, if needed
        platform = state['mxSetup'].get('get_platform', None)
        if platform is not None:
            log.info('setting platform to %r' % platform)
            mx_set_platform(platform)
        
        log.info('restoring build data from a previous build run')
        for sub_command, data in state.items():
            if _debug:
                print 'restoring build data for command %r' % sub_command
            if sub_command == 'mxSetup':
                self.distribution.metadata.version = data['get_version']
                self.distribution.metadata.name = data['get_name']
            elif sub_command == 'build':
                for key, value in data.items():
                    self.__dict__[key] = value
            elif sub_command == 'distribution':
                for key, value in data.items():
                    self.distribution.__dict__[key] = value
            else:
                cmd = self.distribution.get_command_obj(sub_command)
                for key, value in data.items():
                    cmd.__dict__[key] = value

    def run(self):

        # Run the build command
        build.run(self)

        # Save the build data in a build pickle for later reuse,
        # unless this is a prebuilt initiated run
        if not self.prebuilt:
            self.write_build_pickle()

    def has_unixlibs(self):
        return self.distribution.has_unixlibs()

    def has_data_files(self):
        return self.distribution.has_data_files()

    # Add new sub-commands:
    if len(build.sub_commands) > 4:
        raise DistutilsError, 'incompatible distutils version !'
    sub_commands = [('build_clib',    build.has_c_libraries),
                    ('build_unixlib', has_unixlibs),
                    ('mx_autoconf',   build.has_ext_modules),
                    ('build_ext',     build.has_ext_modules),
                    ('build_py',      build.has_pure_modules),
                    ('build_scripts', build.has_scripts),
                    ('build_data',    has_data_files),
                   ]

#
# mx Build C Lib command
#

class mx_build_clib(CompilerSupportMixin,
                    build_clib):

    """ build_clib command which builds the libs using
        separate temp dirs
        
    """
    # Lib of output files
    outfiles = None

    def finalize_options(self):
        
        build_clib.finalize_options(self)
        self.outfiles = []

    def build_library(self, lib_name, build_info):

        # Build each extension in its own subdir of build_temp (to
        # avoid accidental sharing of object files between extensions
        # having the same name, e.g. mxODBC.o).
        build_temp_base = self.build_temp
        self.build_temp = os.path.join(build_temp_base, lib_name)
        compiler = self.prepare_compiler()

        try:

            #
            # This is mostly identical to the original build_clib command.
            #
            sources = build_info.get('sources')
            if sources is None or \
               type(sources) not in (types.ListType, types.TupleType):
                raise DistutilsSetupError, \
                      ("in 'libraries' option (library '%s'), " +
                       "'sources' must be present and must be " +
                       "a list of source filenames") % lib_name
            sources = list(sources)

            log.info("building '%s' library" % lib_name)

            # First, compile the source code to object files in the
            # library directory.  (This should probably change to
            # putting object files in a temporary build directory.)
            macros = build_info.get('macros')
            include_dirs = build_info.get('include_dirs')
            objects = compiler.compile(sources,
                                       output_dir=self.build_temp,
                                       macros=macros,
                                       include_dirs=include_dirs,
                                       debug=self.debug)

            # Now "link" the object files together into a static library.
            # (On Unix at least, this isn't really linking -- it just
            # builds an archive.  Whatever.)
            compiler.create_static_lib(objects, lib_name,
                                       output_dir=self.build_clib,
                                       debug=self.debug)
            
            # Record the name of the library we just created
            self.outfiles.append(
                compiler.library_filename(lib_name,
                                          output_dir=self.build_clib))

        finally:
            # Cleanup local changes to the configuration
            self.build_temp = build_temp_base
        
    def build_libraries(self, libraries):

        for (lib_name, build_info) in libraries:
            self.build_library(lib_name, build_info)

    def get_outputs(self):

        """ Return a list of the created library files.

            This is needed by mx_bdist_prebuilt on all build commands
            and build_clib doesn't provide it.

        """
        return self.outfiles

#
# mx Build Extensions command
#

class mx_build_ext(CompilerSupportMixin,
                   build_ext):

    """ build_ext command which runs mx_autoconf command before
        trying to build anything.
        
    """
    user_options = build_ext.user_options + [
        ('disable-build=', None,
         'disable building an optional extensions (comma separated list of '
         'dotted package names); default is to try building all'),
        ('enable-build=', None,
         'if given, only these optional extensions are built (comma separated '
         'list of dotted package names)'),
        ]

    # mx_autoconf command object (finalized and run)
    autoconf = None

    # Default values for command line options
    disable_build = None
    enable_build = None

    # Extra output files
    extra_output = ()

    # Output files
    output_files = None
    
    def finalize_options(self):

        build_ext.finalize_options(self)
        if self.disable_build is None:
            self.disable_build = ()
        elif type(self.disable_build) is types.StringType:
            self.disable_build = [x.strip()
                                  for x in self.disable_build.split(',')]
        if type(self.enable_build) is types.StringType:
            self.enable_build = [x.strip()
                                 for x in self.enable_build.split(',')]
        self.extra_output = []

    def run(self):

        # Add unixlibs install-dirs to library_dirs, so that linking
        # against them becomes easy
        if self.distribution.has_unixlibs():
            build_unixlib = self.get_finalized_command('build_unixlib')
            paths, libs = build_unixlib.get_unixlib_lib_options()
            # Libraries have to be linked against by defining them
            # in the mx_Extension() setup, otherwise, all extensions
            # get linked against all Unix libs that were built...
            #self.libraries[:0] = libs
            self.library_dirs[:0] = paths
            
        # Assure that mx_autoconf has been run and store a reference
        # in .autoconf
        self.run_command('mx_autoconf')
        self.autoconf = self.get_finalized_command('mx_autoconf')

        # Now, continue with the standard build process
        build_ext.run(self)

    def build_extensions(self):

        # Make sure the compiler is setup correctly
        compiler = self.prepare_compiler()
        
        # Make sure that any autoconf actions use the same compiler
        # settings as we do (the .compiler is set up in build_ext.run()
        # just before calling .build_extensions())
        self.autoconf._set_compiler_object(compiler)

        # Build the extensions
        self.check_extensions_list(self.extensions)
        for ext in self.extensions:
            self.build_extension(ext)

        # Cleanup .extensions list (remove entries which did not build correctly)
        l = []
        for ext in self.extensions:
            if not isinstance(ext, mx_Extension):
                l.append(ext)
            else:
                if ext.successfully_built:
                    l.append(ext)
        self.extensions = l
        if _debug:
            print 'extensions:', repr(self.extensions)
        log.info('')
         
    def build_extension(self, ext):

        required = not hasattr(ext, 'required') or ext.required
        log.info('')
        log.info('building extension "%s" %s' %
                 (ext.name,
                  required * '(required)' or '(optional)'))
        compiler = self.prepare_compiler()

        # Optional extension building can be adjusted via command line options
        if not required:
            if self.enable_build is not None and \
               ext.name not in self.enable_build:
                log.info('skipped -- build not enabled by command line option')
                return
            elif ext.name in self.disable_build:
                log.info('skipped -- build disabled by command line option')
                return

        # Search for include files
        if (isinstance(ext, mx_Extension) and \
            ext.needed_includes):
            log.info('looking for header files needed by extension '
                     '"%s"' % ext.name)
            for filename, dirs, pattern in ext.needed_includes:
                (dir, pathname) = self.autoconf.find_include_file(
                    filename,
                    dirs,
                    pattern)
                if dir is not None:
                    log.info('found needed include file "%s" '
                             'in directory %s' % (filename, dir))
                    if dir not in ext.include_dirs and \
                       dir not in STDINCLPATH and \
                       dir not in INCLPATH:
                        ext.include_dirs.append(dir)
                else:
                    if required:
                        raise CompileError, \
                              'could not find needed header file "%s"' % \
                              filename
                    else:
                        log.warn(
                            '*** WARNING: Building of extension '
                            '"%s" failed: needed include file "%s" '
                            'not found' %
                            (ext.name, filename))
                        return
                    
        # Search for libraries
        if hasattr(ext, 'needed_libraries') and \
           ext.needed_libraries:
            log.info('looking for libraries needed by extension '
                     '"%s"' % ext.name)
            for libname, dirs, pattern in ext.needed_libraries:
                dir, pathname = self.autoconf.find_library_file(
                    libname,
                    dirs,
                    pattern=pattern,
                    lib_types=ext.lib_types)
                if dir is not None:
                    log.info('found needed library "%s" '
                             'in directory %s (%s)' % (libname,
                                                       dir,
                                                       pathname))
                    if 'shared' not in ext.lib_types:
                        # Force static linking and append the library
                        # pathname to the linker arguments
                        if libname in ext.libraries:
                            ext.libraries.remove(libname)
                        if not ext.extra_link_args:
                            ext.extra_link_args = []
                        ext.extra_link_args.append(
                            pathname)
                    else:
                        # Prefer dynamic linking
                        if dir not in ext.library_dirs and \
                           dir not in STDLIBPATH and \
                           dir not in LIBPATH:
                            ext.library_dirs.append(dir)
                        if libname not in ext.libraries:
                            ext.libraries.append(libname)
                    if ext.include_needed_libraries:
                        ext_package_dir = os.path.split(
                            self.get_ext_filename(
                            self.get_ext_fullname(ext.name)))[0]
                        # The linker will always link against the
                        # real name, not a symbolic name (XXX Hope this
                        # is true for all platforms)
                        realpathname = os.path.realpath(pathname)
                        realfilename = os.path.split(realpathname)[1]
                        # Copy the share lib to the package dir, using
                        # the real filename
                        data_entry = (realpathname,
                                      ext_package_dir + os.sep)
                        if data_entry not in ext.data_files:
                            if _debug:
                                print ('adding library data entry %r' %
                                       (data_entry,))
                            ext.data_files.append(data_entry)
                else:
                    if required:
                        raise CompileError, \
                              'could not find needed library "%s"' % \
                              libname
                    else:
                        log.warn(
                            '*** WARNING: Building of extension '
                            '"%s" failed: needed library "%s" '
                            'not found' %
                            (ext.name, libname))
                        return
                    
        # Build each extension in its own subdir of build_temp (to
        # avoid accidental sharing of object files between extensions
        # having the same name, e.g. mxODBC.o).
        build_temp_base = self.build_temp
        extpath = ext.name.replace('.', '-')
        self.build_temp = os.path.join(build_temp_base, extpath)

        # Check for availability of optional libs which can be used
        # by the extension; note: this step includes building small
        # object files to test for the availability of the libraries
        if isinstance(ext, mx_Extension) and \
           ext.optional_libraries:
            log.info("checking for optional libraries")
            for libname, headerfiles in ext.optional_libraries:
                if self.autoconf.check_library(libname, headers=headerfiles):
                    symbol = 'HAVE_%s_LIB' % libname.upper()
                    log.info("found optional library '%s'"
                             " -- defining %s" % (libname, symbol))
                    ext.libraries.append(libname)
                    ext.define_macros.append((symbol, '1'))
                else:
                    log.warn("could not find optional library '%s'"
                             " -- omitting it" % libname)

        if _debug:
            print 'Include dirs:', repr(ext.include_dirs +
                                        compiler.include_dirs)
            print 'Libary dirs:', repr(ext.library_dirs +
                                       compiler.library_dirs)
            print 'Libaries:', repr(ext.libraries)
            print 'Macros:', repr(ext.define_macros)

        # Build the extension
        successfully_built = 0
        try:
            
            # Skip extensions which cannot be built if the required
            # option is given and set to false.
            required = not hasattr(ext, 'required') or ext.required
            if required:
                build_ext.build_extension(self, ext)
                successfully_built = 1
            else:
                try:
                    build_ext.build_extension(self, ext)
                except (CCompilerError, DistutilsError), why:
                    log.warn(
                        '*** WARNING: Building of extension "%s" '
                        'failed: %s' %
                        (ext.name, sys.exc_info()[1]))
                else:
                    successfully_built = 1

        finally:
            # Cleanup local changes to the configuration
            self.build_temp = build_temp_base

        # Processing for successfully built extensions
        if successfully_built:

            if isinstance(ext, mx_Extension):
                # Add Python packages needed by this extension
                self.distribution.packages.extend(ext.packages)

                # Add data files needed by this extension
                self.distribution.data_files.extend(ext.data_files)

            # Mark as having been built successfully
            ext.successfully_built = 1

    def get_outputs(self):

        # Note: The cache is needed for mx_uninstall when used
        # together with mx_bdist_prebuilt. mx_build will run a
        # recursive .get_outputs() on all sub-commands and then store
        # the sub-command objects in the build pickle.  By using a
        # cache, we can avoid to have the command object to have to
        # rebuild the outputs (this may not be possible due to the
        # missing source files).
        if self.output_files is not None:
            return self.output_files
        else:
            files = build_ext.get_outputs(self)
            self.output_files = files
            return files

#
# mx Build Python command
#

class mx_build_py(build_py):

    """ build_py command which also allows removing Python source code
        after the byte-code compile process.
        
    """
    user_options = build_py.user_options + [
        ('without-source', None, "only include Python byte-code"),
        ]

    boolean_options = build_py.boolean_options + ['without-source']

    # Omit source files ?
    without_source = 0

    # Output cache
    output_files = None
    
    def run(self):

        if self.without_source:
            # --without-source implies byte-code --compile
            if (not self.compile and
                not self.optimize):
                self.compile = 1

        # Build the Python code
        build_py.run(self)

        # Optionally remove source code
        if self.without_source:
            log.info('removing Python source files (--without-source)')
            verbose = self.verbose
            dry_run = self.dry_run
            for file in build_py.get_outputs(self, include_bytecode=0):
                # Only process .py files
                if file[-3:] != '.py':
                    continue
                # Remove source code
                execute(os.remove, (file,), "removing %s" % file,
                        verbose=verbose, dry_run=dry_run)
                # Remove .pyc files (if not requested)
                if not self.compile:
                    filename = file + "c"
                    if os.path.isfile(filename):
                        execute(os.remove, (filename,),
                                "removing %s" % filename,
                                verbose=verbose, dry_run=dry_run)
                # Remove .pyo files (if not requested)
                if self.optimize == 0:
                    filename = file + "o"
                    if os.path.isfile(filename):
                        execute(os.remove, (filename,),
                                "removing %s" % filename,
                                verbose=verbose, dry_run=dry_run)

    def get_outputs(self, include_bytecode=1):

        # Note: The cache is needed for mx_uninstall when used
        # together with mx_bdist_prebuilt. See
        # mx_build_ext.get_outputs() for details.

        # Try cache first
        cache_key = include_bytecode
        if self.output_files is not None:
            files = self.output_files.get(cache_key, None)
            if files is not None:
                return files
        else:
            self.output_files = {}

        # Regular processing
        if (not self.without_source or
            not include_bytecode):
            files = build_py.get_outputs(self, include_bytecode)
            self.output_files[cache_key] = files
            return files

        # Remove source code files from outputs
        files = []
        for file in build_py.get_outputs(self, include_bytecode=1):
            if ((self.without_source and file[-3:] == '.py') or
                (not self.compile and file[-4:] == '.pyc') or
                (not self.optimize and file[-4:] == '.pyo')):
                continue
            files.append(file)
        self.output_files[cache_key] = files
        return files
        
#
# mx Build Data command
#

class mx_build_data(Command):

    """ build_data command which allows copying (external) data files
        into the build tree.
        
    """
    description = "build data files (copy them to the build directory)"

    user_options = [
        ('build-lib=', 'b',
         "directory to store built Unix libraries in"),
        ]
    
    boolean_options = []

    # Location of the build directory
    build_lib = None

    def initialize_options(self):

        self.build_lib = None
        self.outfiles = []

    def finalize_options(self):

        self.set_undefined_options('build',
                                   ('verbose', 'verbose'),
                                   ('build_lib', 'build_lib'),
                                   )
        if _debug:
            # For debugging we are always in very verbose mode...
            self.verbose = 2

    def get_outputs(self):

        return self.outfiles

    def build_data_files(self, data_files):

        """ Copy the data_files to the build_lib directory.

            For tuple entries, this updates the data_files list in
            place and adjusts it, so that the data files are picked
            up from the build directory rather than their original
            location.

        """
        build_lib = self.build_lib
        for i in range(len(data_files)):

            entry = data_files[i]
            copied_data_files = []
            
            if type(entry) == types.StringType:
                # Unix- to platform-convention conversion
                entry = convert_to_platform_path(entry)
                filenames = glob.glob(entry)
                for filename in filenames:
                    dst = os.path.join(build_lib, filename)
                    dstdir = os.path.split(dst)[0]
                    if not self.dry_run:
                        self.mkpath(dstdir)
                        outfile = self.copy_file(filename, dst)[0]
                    else:
                        outfile = dst
                    self.outfiles.append(outfile)
                    # Add to the copied_data_files list (using the
                    # distutils internal Unix path format)
                    copied_data_files.append(
                        convert_to_distutils_path(filename))
                    
            elif type(entry) == types.TupleType:
                origin, target = entry
                # Unix- to platform-convention conversion
                origin = convert_to_platform_path(origin)
                target = convert_to_platform_path(target)
                targetdir, targetname = os.path.split(target)
                origin_pathnames = glob.glob(origin)
                if targetname:
                    # Make sure that we don't copy multiple files to
                    # the same target filename
                    if len(origin_pathnames) > 1:
                        raise ValueError(
                            'cannot copy multiple files to %s' %
                            target)
                for pathname in origin_pathnames:
                    if targetname:
                        # Use the new targetname filename
                        filename = targetname
                    else:
                        # Use the original filename
                        filename = os.path.split(pathname)[1]
                    dst = os.path.join(build_lib,
                                       targetdir,
                                       filename)
                    dstdir = os.path.split(dst)[0]
                    if not self.dry_run:
                        self.mkpath(dstdir)
                        outfile = self.copy_file(pathname, dst)[0]
                    else:
                        outfile = dst
                    self.outfiles.append(outfile)
                    # Add to the copied_data_files list (using the
                    # distutils internal Unix path format)
                    copied_data_files.append(
                        convert_to_distutils_path(
                            os.path.join(targetdir,
                                         filename)))

            else:
                raise ValueError('unsupported data_files item format: %r' %
                                 entry)

            # Clear the data_files entry (we'll clean up the list
            # later on)
            data_files[i] = None

            # Add the new copied_data_files to the data_files, so
            # that install_data can pick up the build version of
            # the data file
            data_files.extend(copied_data_files)

        # Cleanup data_files (remove all None, empty and duplicate
        # entries)
        d = {}
        for filename in data_files:
            if not filename:
                continue
            d[filename] = 1
        data_files[:] = d.keys()

        if _debug:
            print 'After build_data: data_files=%r' % data_files
            print 'build_data output=%r' % self.outfiles
        
    def run(self):

        if not self.distribution.data_files:
            return
        self.build_data_files(self.distribution.data_files)

#
# mx Build Unix Libs command
#
class UnixLibrary:

    """ Container for library configuration data.
    """
    # Name of the library
    libname = ''

    # Source tree where the library lives
    sourcetree = ''

    # List of library files and where to install them in the
    # build tree
    libfiles = None

    # Name of the configure script
    configure = 'configure'

    # Configure options
    configure_options = None

    # Make options
    make_options = None
    
    def __init__(self, libname, sourcetree, libfiles,
                 configure=None, configure_options=None,
                 make_options=None):

        self.libname = libname
        self.sourcetree = sourcetree
        # Check for 2-tuples...
        for libfile, targetdir in libfiles:
            pass
        self.libfiles = libfiles

        # Optional settings
        if configure:
            self.configure = configure
        if configure_options:
            self.configure_options = configure_options
        else:
            self.configure_options = []
        if make_options:
            self.make_options = make_options
        else:
            self.make_options = []
            
    def get(self, option, alternative=None):

        return getattr(self, option, alternative)

class mx_build_unixlib(Command):

    """ This command compiles external libs using the standard Unix
        procedure for this:
        
        ./configure
        make

    """
    description = "build Unix libraries used by Python extensions"

    # make program to use
    make = None
    
    user_options = [
        ('build-lib=', 'b',
         "directory to store built Unix libraries in"),
        ('build-temp=', 't',
         "directory to build Unix libraries to"),
        ('make=', None,
         "make program to use"),
        ('makefile=', None,
         "makefile to use"),
        ('force', 'f',
         "forcibly reconfigure"),
        ]
    
    boolean_options = ['force']

    def initialize_options(self):

        self.build_lib = None
        self.build_temp = None
        self.make = None
        self.makefile = None
        self.force = 0

    def finalize_options(self):

        self.set_undefined_options('build',
                                   ('verbose', 'verbose'),
                                   ('build_lib', 'build_lib'),
                                   ('build_temp', 'build_temp')
                                   )
        if self.make is None:
            self.make = 'make'
        if self.makefile is None:
            self.makefile = 'Makefile'

        if _debug:
            # For debugging we are always in very verbose mode...
            self.verbose = 2

    def run_script(self, script, options=[]):

        if options:
            l = []
            for k, v in options:
                if v is not None:
                    l.append('%s=%s' % (k, v))
                else:
                    l.append(k)
            script = script + ' ' + ' '.join(l)
        log.info('executing script %s' % repr(script))
        if self.dry_run:
            return 0
        try:
            rc = os.system(script)
        except DistutilsExecError, msg:
            raise CompileError, msg
        return rc
    
    def run_configure(self, options=[], dir=None, configure='configure'):

        """ Run the configure script using options is given.

            Options must be a list of tuples (optionname,
            optionvalue).  If an option should not have a value,
            passing None as optionvalue will have the effect of using
            the option without value.

            dir can be given to have the configure script execute in
            that directory instead of the current one.

        """
        cmd = './%s' % configure
        if dir:
            cmd = 'cd %s; ' % dir + cmd
        log.info('running %s in %s' % (configure, dir or '.'))
        rc = self.run_script(cmd, options)
        if rc != 0:
            raise CompileError, 'configure script failed'

    def run_make(self, targets=[], dir=None, make='make', options=[]):

        """ Run the make command for the given targets.

            Targets must be a list of valid Makefile targets.

            dir can be given to have the make program execute in that
            directory instead of the current one.

        """
        cmd = '%s' % make
        if targets:
            cmd = cmd + ' ' + ' '.join(targets)
        if dir:
            cmd = 'cd %s; ' % dir + cmd
        log.info('running %s in %s' % (make, dir or '.'))
        rc = self.run_script(cmd, options)
        if rc != 0:
            raise CompileError, 'make failed'

    def build_unixlib(self, unixlib):

        # Build each lib in its own subdir of build_temp (to
        # avoid accidental sharing of object files)
        build_temp_base = self.build_temp
        libpath = unixlib.libname
        self.build_temp = os.path.join(build_temp_base, libpath)

        try:

            # Get options
            configure = unixlib.configure
            configure_options = unixlib.configure_options
            make_options = unixlib.make_options
            sourcetree = unixlib.sourcetree
            buildtree = os.path.join(self.build_temp, sourcetree)
            libfiles = unixlib.libfiles
            if not libfiles:
                raise DistutilsError, \
                      'no libfiles defined for unixlib "%s"' % \
                      unixlib.name
            log.info('building C lib %s in %s' % (unixlib.libname,
                                                  buildtree))
            # Prepare build
            log.info('preparing build of %s' % unixlib.libname)
            self.mkpath(buildtree)
            self.copy_tree(sourcetree, buildtree)

            # Run configure to build the Makefile
            if not os.path.exists(os.path.join(buildtree, self.makefile)) or \
               self.force:
                self.run_configure(configure_options,
                                   dir=buildtree,
                                   configure=configure)
            else:
                log.info("skipping configure: "
                         "%s is already configured" %
                         unixlib.libname)

            # Run make
            self.run_make(dir=buildtree,
                          make=self.make,
                          options=make_options)

            # Copy libs to destinations
            for sourcefile, destination in libfiles:
                if not destination:
                    continue
                sourcefile = os.path.join(self.build_temp, sourcefile)
                destination = os.path.join(self.build_lib, destination)
                if not os.path.exists(sourcefile):
                    raise CompileError, \
                          'library "%s" failed to build' % sourcefile
                self.mkpath(destination)
                self.copy_file(sourcefile, destination)

        finally:
            # Cleanup local changes to the configuration
            self.build_temp = build_temp_base

    def build_unixlibs(self, unixlibs):

        for unixlib in unixlibs:
            self.build_unixlib(unixlib)

    def get_unixlib_lib_options(self):

        libs = []
        paths = []
        for unixlib in self.distribution.unixlibs:
            for sourcefile, destination in unixlib.libfiles:
                if not destination:
                    # direct linking
                    sourcefile = os.path.join(self.build_temp,
                                              sourcefile)
                    libs.append(sourcefile)
                else:
                    # linking via link path and lib name
                    sourcefile = os.path.basename(sourcefile)
                    libname = os.path.splitext(sourcefile)[0]
                    if libname[:3] == 'lib':
                        libname = libname[3:]
                    libs.append(libname)
                    destination = os.path.join(self.build_lib,
                                               destination)
                    paths.append(destination)
        #print paths, libs
        return paths, libs

    def run(self):

        if not self.distribution.unixlibs:
            return
        self.build_unixlibs(self.distribution.unixlibs)

#
# mx Install command
#

class mx_install(install):

    """ We want install_data to default to install_purelib, if it is
        not given.

    """
    # build_lib attribute copied to the install command from the
    # build command during .finalize_options()
    build_lib = None

    # Force installation into the platlib, even if the package is a
    # pure Python library
    force_non_pure = 0
    
    user_options = install.user_options + [
        ('force-non-pure', None,
         "force installation into the platform dependent directory"),
        ]

    def initialize_options(self):

        install.initialize_options(self)
        self.force_non_pure = 0
    
    def finalize_options(self):

        fix_install_data = (self.install_data is None)
            
        install.finalize_options(self)

        # Force installation into the platform dependent directories,
        # even if this package is a pure Python package
        if self.force_non_pure:
            self.install_purelib = self.install_platlib
            self.install_libbase = self.install_platlib
            self.install_lib = os.path.join(self.install_platlib,
                                            self.extra_dirs)

        # We want install_data to default to install_purelib, if it is
        # not given.
        if fix_install_data:
            # We want data to be installed alongside the Python
            # modules
            self.install_data = self.install_purelib

        # Undo the change introduced in Python 2.4 to bdist_wininst
        # which manipulates the build.build_lib path and adds
        # a target_version specific ending; we simply override
        # the value here (rather than in build), since all install_*
        # commands pick up the .build_lib value from this command
        # rather than build.
        if self.distribution.has_ext_modules():
            build = self.get_finalized_command('build')
            if _debug:
                print ('resetting build_lib from "%s" to "%s"' %
                       (self.build_lib,
                        build.build_platlib))
            self.build_lib = build.build_platlib

        self.dump_dirs('after applying mx_install fixes')

    def ensure_finalized(self):

        install.ensure_finalized(self)

        # Hack needed for bdist_wininst
        if self.install_data[-5:] == '\\DATA':
            # Install data into the Python module part
            self.install_data = self.install_data[:-5] + '\\PURELIB'

#
# mx Install Data command
#

class mx_install_data(install_data):

    """ Rework the install_data command to something more useful.

        Two data_files formats are supported:

        * string entries
        
            The files (which may include wildcards) are copied to the
            installation directory using the same relative path.

        * tuple entries of the form (orig, dest)

            The files given in orig (which may include wildcards) are
            copied to the dest directory relative to the installation
            directory.

            If dest includes a filename, the file orig is copied to
            the file dest. Otherwise, the original filename is used
            and the file copied to the dest directory.
    
    """

    user_options = install_data.user_options + [
        ('build-lib=', 'b',
         "directory to store built Unix libraries in"),
        ]

    def initialize_options(self):

        self.build_lib = None
        install_data.initialize_options(self)

    def finalize_options(self):

        if self.install_dir is None:
            installobj = self.distribution.get_command_obj('install')
            self.install_dir = installobj.install_data
        if _debug:
            print 'Installing data files to %s' % self.install_dir
        self.set_undefined_options('install',
                                   ('build_lib', 'build_lib'),
                                   )
        install_data.finalize_options(self)

    def run(self):

        if not self.dry_run:
            self.mkpath(self.install_dir)
        data_files = self.get_inputs()
        if _debug:
            print 'install_data: data_files=%r' % self.data_files
        for entry in data_files:

            if type(entry) == types.StringType:
                # Unix- to platform-convention conversion
                entry = convert_to_platform_path(entry)
                # Names in data_files are now relative to the build
                # directory, since mx_build_data has copied them there
                entry = os.path.join(self.build_lib, entry)
                filenames = glob.glob(entry)
                for filename in filenames:
                    relative_filename = remove_path_prefix(
                        filename, self.build_lib)
                    dst = os.path.join(self.install_dir, relative_filename)
                    dstdir = os.path.split(dst)[0]
                    if not self.dry_run:
                        self.mkpath(dstdir)
                        outfile = self.copy_file(filename, dst)[0]
                    else:
                        outfile = dst
                    self.outfiles.append(outfile)

            else:
                raise ValueError('unsupported data_files item format: %r' %
                                 (entry,))

        if _debug:
            print 'install_data: outfiles=%r' % self.outfiles

#
# mx Install Lib command
#

class mx_install_lib(install_lib):

    """ Patch the install_lib to work around a problem where the
        .get_outputs() method would return filenames like '.pyoo',
        '.pyco', etc.
        
    """
    def _bytecode_filenames (self, filenames):

        """ Create a list of byte-code filenames from the list of
            filenames.

            Files in filenames that are not Python source code are
            ignored.

        """
        bytecode_filenames = []
        for py_file in filenames:
            if py_file[-3] != '.py':
                continue
            if self.compile:
                bytecode_filenames.append(py_file + "c")
            if self.optimize > 0:
                bytecode_filenames.append(py_file + "o")
        return bytecode_filenames

#
# mx Uninstall command
#
# Credits are due to Thomas Heller for the idea and the initial code
# base for this command (he posted a different version to
# distutils-sig@python.org) in 02/2001.
#

class mx_uninstall(Command):

    description = "uninstall the package files and directories"

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass
        
    def run(self):

        # Execute build
        log.info('determining installation files')
        log.info('(re)building package')
        savevalue = self.distribution.dry_run
        self.distribution.dry_run = 0
        self.run_command('build')

        # Execute install in dry-run mode
        log.debug('dry-run package install (to determine the installed files)')
        self.distribution.dry_run = 1
        self.run_command('install')
        self.distribution.dry_run = savevalue
        build = self.get_finalized_command('build')
        install = self.get_finalized_command('install')

        # Remove all installed files
        log.info('removing installed files')
        dirs = {}
        filenames = install.get_outputs()
        for filename in filenames:
            if not os.path.isabs(filename):
                raise DistutilsError,\
                      'filename %s from .get_output() not absolute' % \
                      filename

            if os.path.isfile(filename):
                log.info('removing %s' % filename)
                if not self.dry_run:
                    try:
                        os.remove(filename)
                    except OSError, details:
                        log.warn('could not remove file: %s' % details)
                    dir = os.path.split(filename)[0]
                    if not dirs.has_key(dir):
                        dirs[dir] = 1
                    if os.path.splitext(filename)[1] == '.py':
                        # Remove byte-code files as well
                        try:
                            os.remove(filename + 'c')
                        except OSError:
                            pass
                        try:
                            os.remove(filename + 'o')
                        except OSError:
                            pass

            elif os.path.isdir(filename):
                if not dirs.has_key(dir):
                    dirs[filename] = 1

            elif not os.path.splitext(filename)[1] in ('.pyo', '.pyc'):
                log.warn('skipping removal of %s (not found)' %
                         filename)

        # Remove the installation directories
        log.info('removing directories')
        dirs = dirs.keys()
        dirs.sort(); dirs.reverse() # sort descending
        for dir in dirs:
            # Don't remove directories which are listed on sys.path
            if dir in sys.path:
                continue
            # Check the the directory is empty
            dir_content = os.listdir(dir)
            if dir_content:
                log.info('directory %s is not empty - not removing it' %
                         dir)
                continue
            # Remove the directory and warn if this fails
            log.info('removing directory %s' % dir)
            if not self.dry_run:
                try:
                    os.rmdir(dir)
                except OSError, details:
                    log.warn('could not remove directory: %s' % details)

#
# mx register command
#

class mx_register(register):

    """ Register a package with PyPI.

        This version enhances the download_url by optionally adding a
        hash tag to it. The command fetches the current contents of
        the referenced URL and calculates the hash value from it.

    """
    # Add new option --add-hash-tag
    user_options = register.user_options + [
        ('add-hash-tag', None,
         'add a hash tag to the download_url'),
        ]
    boolean_options = register.boolean_options + [
        'add-hash-tag',
        ]

    def initialize_options(self):

        self.add_hash_tag = None
        register.initialize_options(self)

    def finalize_options(self):

        if self.add_hash_tag is None:
            self.add_hash_tag = False
        register.finalize_options(self)

    def run(self):

        if self.add_hash_tag:
            download_url = self.distribution.metadata.download_url
            if download_url:
                download_url = mx_download_url(
                    download_url,
                    'simple')
                log.info('updating download_url to %r' % download_url)
                self.distribution.metadata.download_url = download_url
        register.run(self)

#
# mx clean command
#

class mx_clean(clean):

    """ Clean up the build directories.

        This version knows about the build pickle.

    """
    def run(self):

        if self.all:
            # Only remove the build pickle, if --all is requested
            build = self.get_finalized_command('build')
            build_pickle = build.get_build_pickle_pathname()
            if os.path.exists(build_pickle):
                log.info('removing %r' % build_pickle)
                try:
                    os.remove(build_pickle)
                except OSError, details:
                    log.warn('could not remove build pickle %s: %s' %
                             (build_pickle, details))

        clean.run(self)

#
# mx sdist command
#

class mx_sdist(sdist):

    """ Build a source distribution.

        This version does not use hard links when preparing the source
        archive - hard links don't match well with symlinks which we
        use in our source repositories.

    """
    def make_release_tree(self, base_dir, files):

        # Prepare release dir
        self.mkpath(base_dir)
        self.distribution.metadata.write_pkg_info(base_dir)
        if not files:
            log.warn('no files found in release !')
            return

        # Create dir structure
        log.info('preparing release tree in %s...' % base_dir)
        create_tree(base_dir, files, dry_run=self.dry_run)
        for file in files:
            if not os.path.isfile(file):
                log.warn('%s is not a regular file -- skipping' % file)
            else:
                dest = os.path.join(base_dir, file)
                self.copy_file(file, dest, link=None)

#
# mx generic binary distribution command
#

class mx_bdist(bdist):

    """ Generic binary distribution command.
    
    """
    
    def finalize_options(self):

        # Default to <platform>-<pyversion> on all platforms
        if self.plat_name is None:
            self.plat_name = '%s-py%s' % (mx_get_platform(), py_version())
        bdist.finalize_options(self)


#
# mx RPM distribution command
#

class mx_bdist_rpm(bdist_rpm):

    """ bdist_rpm command which allows passing in distutils
        options.

        XXX Note: bdist_rpm no longer works for some reason, probably
            related to distutils rather than our small modification.

    """
    user_options = bdist_rpm.user_options + [
        ('distutils-build-options=', None,
         'extra distutils build options to use before the "build" command'),
        ('distutils-install-options=', None,
         'extra distutils install options to use after the "install" command'),
        ]

    # Defaults
    distutils_build_options = None
    distutils_install_options = None

    def finalize_options(self):

        bdist_rpm.finalize_options(self)
        if self.distutils_build_options is None:
            self.distutils_build_options = ''
        if self.distutils_install_options is None:
            self.distutils_install_options = ''

    def _make_spec_file(self):

        # Generate .spec file
        l = bdist_rpm._make_spec_file(self)

        # Insert into build command
        i = l.index('%build')
        buildcmd = l[i + 1]
        inspos = l[i + 1].find(' build')
        if inspos >= 0:
            l[i + 1] = '%s %s %s' % (buildcmd[:inspos],
                                     self.distutils_build_options,
                                     buildcmd[inspos:])
        else:
            raise DistutilsError, \
                  'could not insert distutils command in RPM build command'
        
        # Insert into install command
        i = l.index('%install')
        installcmd = l[i + 1]
        inspos = l[i + 1].find(' install')
        if inspos >= 0:
            l[i + 1] = '%s %s %s %s' % (installcmd[:inspos],
                                        self.distutils_build_options,
                                        installcmd[inspos:],
                                        self.distutils_install_options)
        else:
            raise DistutilsError, \
                  'could not insert distutils command in RPM install command'

        return l
    
#
# mx bdist_wininst command
#

class mx_bdist_wininst(bdist_wininst):

    """ We want bdist_wininst to include the Python version number
        even for pure Python distribution - in case we don't include
        the Python source code.

    """
    
    def finalize_options(self):

        bdist_wininst.finalize_options(self)

        # Force a target version if without_source was used for
        # build_py
        if not self.target_version:
            build_py = self.get_finalized_command('build_py')
            if build_py.without_source:
                self.target_version = py_version(unicode_aware=0)

#
# mx in-place binary distribution command
#

class mx_bdist_inplace(bdist_dumb):

    """ Build an in-place binary distribution.
    
    """

    # Path prefix to use in the distribution (all files will be placed
    # under this prefix)
    dist_prefix = ''

    user_options = bdist_dumb.user_options + [
        ('dist-prefix=', None,
         'path prefix the binary distribution with'),
        ]

    def finalize_options(self):

        # Default to ZIP as format on all platforms
        if self.format is None:
            self.format = 'zip'
        bdist_dumb.finalize_options(self)

    # Hack to reuse bdist_dumb for our purposes; .run() calls
    # reinitialize_command() with 'install' as command.
    def reinitialize_command(self, command, reinit_subcommands=0):

        cmdobj = bdist_dumb.reinitialize_command(self, command,
                                                 reinit_subcommands)
        if command == 'install':
            cmdobj.install_lib = self.dist_prefix
            cmdobj.install_data = self.dist_prefix
        return cmdobj

#
# mx Zope binary distribution command
#

class mx_bdist_zope(mx_bdist_inplace):

    """ Build binary Zope product distribution.
    
    """

    # Path prefix to use in the distribution (all files will be placed
    # under this prefix); for Zope instances, all code can be placed
    # into the Zope instance directory since this is on sys.path when
    # Zope starts
    dist_prefix = ''

#
# mx bdist_prebuilt command
#

class mx_bdist_prebuilt(mx_sdist):

    """ Build a pre-built distribution.

        The idea is to ship a version of the package that is already
        built, but not yet packaged or installed.

        This makes it possible to do that last step on the clients
        target machine, giving much more flexibility in the way
        software is installed.

    """
    # Skip the build process ?
    skip_build = None

    # Platform name to use
    plat_name = None

    # Keep data source files
    include_data_source_files = None

    # Files to exclude from the prebuilt archives
    exclude_files = None

    # File name version
    #
    # Version 1 format (not easy_install compatible):
    # product_name + '-' + version + '.' + platform + '-' + python_ucs + '.prebuilt.zip'
    #
    # Version 2 format (easy_install compatible):
    # product_name + '-' + version + '-' + python_ucs + '-' + platform + '-prebuilt.zip'
    #
    filename_version = 2

    user_options = mx_sdist.user_options + [
        ('plat-name=', None,
         'platform name to use'),
        ('skip-build', None,
         'skip build and reuse the existing build files'),
        ('include-data-source-files', None,
         'include the data source files '
         'in addition to the build versions'),
        ('exclude-files', None,
         'exclude files matching the given RE patterns '
         '(separated by whitespace)'),
        ]

    def finalize_options(self):

        if self.plat_name is None:
            build = self.get_finalized_command('build')
            if (not build.has_ext_modules() and
                not build.has_c_libraries() and
                not build.has_unixlibs() and
                not sys.platform.startswith('win')):
                # We can build a platform independent distribution;
                # note that we cannot build platform independent
                # distributions on Windows, since all path names will
                # use the Windows os.sep which doesn't work on Unix
                # platforms.
                self.plat_name = 'py%s' % py_version(unicode_aware=0)
            else:
                # Include the platform name
                if self.filename_version == 1:
                    self.plat_name = '%s-py%s' % (
                        mx_get_platform(),
                        py_version())
                elif self.filename_version == 2:
                    self.plat_name = 'py%s-%s' % (
                        py_version(),
                        mx_get_platform())
                else:
                    raise TypeError('unsupported .filename_version')

        # Skip the build step ?
        if self.skip_build is None:
            self.skip_build = 0

        # Include data source files ?
        if self.include_data_source_files is None:
            self.include_data_source_files = 0

        # Exclude files ?
        if self.exclude_files is None:
            self.exclude_files = []
        else:
            self.exclude_files = [re.compile(pattern.strip())
                                  for pattern in self.exclude_files.split()]

        # Default to ZIP files for all platforms
        if self.formats is None:
            self.formats = ['zip']

        # Call the base method
        mx_sdist.finalize_options(self)

    def get_file_list(self):

        log.info('building list of files to include in the pre-built distribution')
        if not os.path.isfile(self.manifest):
            log.error('manifest missing: '
                      'cannot create pre-built distribution')
            return
        self.read_manifest()

        # Prepare a list of source files needed for install_data
        data_source_files = []
        for entry in self.distribution.data_files:
            if type(entry) is types.TupleType:
                (source_file, dest_file) = entry
            else:
                source_file = entry
            source_file = convert_to_platform_path(source_file)
            data_source_files.append(source_file)
        if _debug:
            print 'found these data source files: %r' % data_source_files

        # Remove most subdirs from the MANIFEST file list
        files = []
        for path in self.filelist.files:
            
            # Note: the MANIFEST file list can use both os.sep and the
            # distutils dir separator as basis

            # Filter files which are not to be included in the archive;
            # we use the distutils path for the filtering
            distutils_path = convert_to_distutils_path(path)
            skip_path = False
            for pattern_re in self.exclude_files:
                if pattern_re.match(distutils_path) is not None:
                    skip_path = True
                    break
            if skip_path:
                if _debug:
                    print '  skipping excluded file: %s' % path
                continue

            # Now filter the remaining files; we'll convert the path
            # the platform version for this
            path = convert_to_platform_path(path)
            if os.sep in path:
                # Subdir entry
                path_components = path.split(os.sep)
                if path_components[0].lower().startswith('doc'):
                    # Top-level documentation directories are always included
                    if _debug:
                        print '  found documentation file: %s' % path
                elif (self.include_data_source_files and
                      path in data_source_files):
                    # Data source files can optionally be included as
                    # well; these will already be in the build area
                    # due to mx_build_data
                    if _debug:
                        print '  found data source file: %s' % path
                else:
                    # Skip all other files in subdirectories
                    if _debug:
                        print '  skipping file: %s' % path
                    continue
            elif _debug:
                print '  found top-level file: %s' % path
            log.info('adding %s' % path)
            files.append(path)

        self.filelist.files = files

        # Add build files
        build = self.get_finalized_command('build')
        self.filelist.files.extend(build.get_outputs())

        if _debug:
            print 'pre-built files:', repr(self.filelist.files)
                
    def run(self):

        if not self.skip_build:
            self.run_command('build')

        mx_sdist.run(self)

    def make_distribution(self):

        if self.filename_version == 1:
            # Version 1 format (not easy_install compatible)
            archive_name = '%s.%s.prebuilt' % (
                self.distribution.get_fullname(),
                self.plat_name)
        elif self.filename_version == 2:
            # Version 2 format (easy_install compatible)
            archive_name = '%s-%s-prebuilt' % (
                self.distribution.get_fullname(),
                self.plat_name)
        else:
            raise TypeError('unsupported .filename_version')
        archive_path = os.path.join(self.dist_dir, archive_name)

        # Create the release tree
        self.make_release_tree(archive_name, self.filelist.files)

        # Add pre-built marker file containing the path to the build
        # pickle with the build information
        prebuilt_pathname = os.path.join(archive_name, PREBUILT_MARKER)
        prebuilt_file = open(prebuilt_pathname, 'w')
        build = self.get_finalized_command('build')
        prebuilt_file.write(build.get_build_pickle_pathname())
        prebuilt_file.close()

        # Create the requested archives
        archive_files = []
        for fmt in self.formats:
            file = self.make_archive(archive_path, fmt, base_dir=archive_name)
            archive_files.append(file)
            # XXX Not sure what .dist_files is good for...
            #self.distribution.dist_files.append(('sdist', '', file))
        self.archive_files = archive_files

        # Remove the release tree
        if not self.keep_temp:
            remove_tree(archive_name, dry_run=self.dry_run)

#
# mx egg binary distribution command
#

class mx_bdist_egg(bdist_dumb):

    """ Build an egg binary distribution.

        This is essentially a bdist_dumb ZIP archive with a special
        name and an .egg extension.

        In addition to the distribution files, it also contains an
        EGG-INFO directory with some additional meta-information about
        the package.
    
    """
    # Build a Unicode-aware egg ? easy_install does not support having
    # UCS2/UCS4 markers in the filename, so we place the egg files
    # into ucs2/ucs4 subdirectories of the --dist-dir if this option
    # is set. Default is not to use these subdirs.
    unicode_aware = None

    user_options = [
        ('plat-name=', 'p',
         'platform name to embed in generated filenames '
         '(default: %s)' % mx_get_platform()),
        ('skip-build', None,
         'skip rebuilding everything (for testing/debugging)'),
        ('dist-dir=', 'd',
         'directory where to put the .egg file'),
        ('unicode-aware', None,
         'put eggs into ucs2/ucs4 subdirectories of --dist-dir'),
        ]

    def finalize_options(self):

        if self.plat_name is None:
            build = self.get_finalized_command('build')
            if (not build.has_ext_modules() and
                not build.has_c_libraries() and
                not build.has_unixlibs()):
                # We can build a platform independent distribution
                self.plat_name = ''
            else:
                # Include the platform name
                self.plat_name = mx_get_platform()

        if self.unicode_aware is None:
            self.unicode_aware = 0

        bdist_dumb.finalize_options(self)

        if self.unicode_aware:
            # Put the eggs into separate dist_dir subdirectories in
            # case unicode aware eggs are to be built
            unicode_subdir = py_unicode_build()
            if unicode_subdir:
                self.dist_dir = os.path.join(self.dist_dir,
                                             unicode_subdir)

    def write_egg_info_file(self, egg_info_dir, filename, lines=()):

        f = open(os.path.join(egg_info_dir, filename), 'wb')
        f.write('\n'.join(lines))
        if lines:
            f.write('\n')
        f.close()

    def run(self):

        if not self.skip_build:
            self.run_command('build')

        # Install the package in the .bdist_dir
        install = self.reinitialize_command('install', reinit_subcommands=1)
        install.root = self.bdist_dir
        install.skip_build = self.skip_build
        install.warn_dir = 0
        # Use an in-place install without prefix
        install.install_lib = ''
        install.install_data = ''
        log.info("installing to %s" % self.bdist_dir)
        self.run_command('install')

        # Remove .egg-info file
        if python_version >= '2.5':
            # install_egg_info was added in Python 2.5 distutils
            install_egg_info = self.get_finalized_command('install_egg_info')
            for filename in install_egg_info.outputs:
                execute(os.remove, (filename,),
                        "removing %s" % filename,
                        verbose=self.verbose, dry_run=self.dry_run)
            install_egg_info.output = []

        # Create EGG-INFO dir in .bdist_dir
        egg_info_dir = os.path.join(self.bdist_dir, 'EGG-INFO')
        self.mkpath(egg_info_dir)
        if not self.dry_run:
            
            # add PKG-INFO file
            self.distribution.metadata.write_pkg_info(egg_info_dir)

            # add not-zip-safe marker to force unzipping the .egg file
            self.write_egg_info_file(egg_info_dir,
                                     'not-zip-safe')

            # add requires.txt
            if python_version >= '2.5':
                self.write_egg_info_file(egg_info_dir,
                                         'requires.txt',
                                         self.distribution.metadata.get_requires())

            # add namespace_packages.txt
            self.write_egg_info_file(egg_info_dir,
                                     'namespace_packages.txt',
                                     self.distribution.namespace_packages)

            # add top_level.txt
            top_level_modules = find_python_modules(self.bdist_dir)
            for namespace_package in self.distribution.namespace_packages:
                if '.' in namespace_package:
                    namespace_package = namespace_package.split('.')[0]
                if namespace_package not in top_level_modules:
                    top_level_modules[namespace_package] = 'namespace'
            self.write_egg_info_file(egg_info_dir,
                                     'top_level.txt',
                                     top_level_modules.keys())
                
            # add dependency_links.txt
            self.write_egg_info_file(egg_info_dir,
                                     'dependency_links.txt',
                                     self.distribution.dependency_links)

            # Add namespace module __init__.py files
            for namespace_package in self.distribution.namespace_packages:
                package_dir = os.path.join(self.bdist_dir,
                                           namespace_package.replace('.', os.sep))
                # We overwrite any existing files, if necessary
                init_file = os.path.join(package_dir, '__init__.py')
                if os.path.exists(init_file):
                    log.info('overwriting %s with setuptools namespace version' %
                             init_file)
                else:
                    log.info('adding %s with setuptools namespace marker' %
                             init_file)
                open(init_file, 'w').write(SETUPTOOLS_NAMESPACE_INIT)
                # Remove any existing byte code files
                for bytecode_suffix in ('c', 'o'):
                    filename = init_file + bytecode_suffix
                    if os.path.exists(filename):
                        execute(os.remove, (filename,),
                                "removing %s" % filename,
                                verbose=self.verbose)

        # Build egg file from .bdist_dir
        egg_name = self.distribution.metadata.get_name().replace('-', '_')
        if self.plat_name:
            unicode_aware = False # self.unicode_aware
        else:
            unicode_aware = False
        archive_basename = "%s-%s-py%s" % (
            egg_name,
            self.distribution.metadata.get_version(),
            py_version(unicode_aware=unicode_aware))
        if self.plat_name:
            archive_basename += '-' + self.plat_name
        archive_basepath = os.path.join(self.dist_dir, archive_basename)
        archive_root = self.bdist_dir
        zip_filename = self.make_archive(archive_basepath, format='zip',
                                         root_dir=archive_root)
        assert zip_filename.endswith('.zip')
        egg_filename = zip_filename[:-4] + '.egg'
        if os.path.exists(egg_filename):
            execute(os.remove, (egg_filename,),
                    "removing %s" % egg_filename,
                    verbose=self.verbose, dry_run=self.dry_run)
        self.move_file(zip_filename, egg_filename)

        # Add to distribution files
        if python_version >= '2.5':
            # This features was added in Python 2.5 distutils
            if self.distribution.has_ext_modules():
                pyversion = get_python_version()
            else:
                pyversion = 'any'
            self.distribution.dist_files.append(('mx_bdist_egg', pyversion,
                                                 egg_filename))

        # Cleanup
        if not self.keep_temp:
            remove_tree(self.bdist_dir, dry_run=self.dry_run)

#
# mx MSI distribution command
#

if bdist_msi is not None:

    class mx_bdist_msi(bdist_msi):

        """ Build an MSI installer.

            This version allows to customize the product name used for
            the installer.

        """
        # Product name to use for the installer (this is the name that
        # gets displayed in the dialogs and on the installed software
        # list)
        product_name = None

        # Product title to use for the installer
        title = None

        # Platform name to use in the installer filename (new in Python 2.6)
        plat_name = None

        user_options = bdist_msi.user_options + [
            ('product-name=', None,
             'product name to use for the installer'),
            ('title=', None,
             'product title to use for the installer'),
            ]

        def finalize_options(self):

            # Force a target version if without_source was used for
            # build_py; this is needed since bdist_msi start to
            # default to installing to all available Python versions,
            # if no .target_version is given for Python 2.7+
            build_py = self.get_finalized_command('build_py')
            if build_py.without_source:
                self.target_version = py_version(unicode_aware=0)

            bdist_msi.finalize_options(self)
            
            if self.title is None:
                self.title = self.distribution.get_fullname()

            # Inherit the .plat_name from the bdist command
            self.set_undefined_options('bdist',
                                       ('plat_name', 'plat_name'),
                                       )


        # XXX This is basically a copy of bdist_msi.run(), restructured
        #     a bit.

        def run_install(self):

            if not self.skip_build:
                self.run_command('build')

            install = self.reinitialize_command('install', reinit_subcommands=1)
            install.prefix = self.bdist_dir
            install.skip_build = self.skip_build
            install.warn_dir = 0

            install_lib = self.reinitialize_command('install_lib')
            # we do not want to include pyc or pyo files
            install_lib.compile = 0
            install_lib.optimize = 0

            if self.distribution.has_ext_modules():
                # If we are building an installer for a Python version other
                # than the one we are currently running, then we need to ensure
                # our build_lib reflects the other Python version rather than ours.
                # Note that for target_version!=sys.version, we must have skipped the
                # build step, so there is no issue with enforcing the build of this
                # version.
                target_version = self.target_version
                if not target_version:
                    assert self.skip_build, "Should have already checked this"
                    target_version = python_version
                plat_specifier = ".%s-%s" % (self.plat_name, target_version)
                build = self.get_finalized_command('build')
                build.build_lib = os.path.join(build.build_base,
                                               'lib' + plat_specifier)

            log.info("installing to %s", self.bdist_dir)
            install.ensure_finalized()

            # avoid warning of 'install_lib' about installing
            # into a directory not in sys.path
            sys.path.insert(0, os.path.join(self.bdist_dir, 'PURELIB'))

            install.run()

            del sys.path[0]

        def get_product_version(self):

            # ProductVersion must be strictly numeric
            version = self.distribution.metadata.get_version()
            try:
                return '%d.%d.%d' % StrictVersion(version).version
            except ValueError:
                # Remove any pre-release or snapshot parts
                try:
                    verstuple = parse_mx_version(version)
                except ValueError:
                    raise DistutilsError(
                        'package version must be formatted with mx_version()')
                major, minor, patch = verstuple[:3]
                new_version = mx_version(major, minor, patch)
                log.warn(
                    "bdist_msi requires strictly numeric "
                    "version numbers: "
                    "using %r for MSI installer, instead of %r" %
                    (new_version, version))
                return new_version

        def get_product_name(self):

            # User defined product name
            if self.product_name is not None:
                product_name = self.product_name

            else:
                # Emulate bdist_msi default behavior, but make the
                # product title changeable.
                #
                # Prefix ProductName with Python x.y, so that
                # it sorts together with the other Python packages
                # in Add-Remove-Programs (APR)
                if self.target_version:
                    product_name = (
                        'Python %s %s %s' % (
                            self.target_version,
                            self.title,
                            self.distribution.metadata.get_version()))
                else:
                    # Group packages under "Python 2.x" if no
                    # .target_version is given
                    product_name = (
                        'Python 2.x %s %s' % (
                            self.title,
                            self.distribution.metadata.get_version()))
            log.info('using %r as product name.' % product_name)
            return product_name

        def run (self):

            self.run_install()

            # Create the installer
            self.mkpath(self.dist_dir)
            fullname = self.distribution.get_fullname()
            installer_name = self.get_installer_filename(fullname)
            log.info('creating MSI installer %s' % installer_name)
            installer_name = os.path.abspath(installer_name)
            if os.path.exists(installer_name):
                os.unlink(installer_name)

            metadata = self.distribution.metadata
            author = metadata.author
            if not author:
                author = metadata.maintainer
            if not author:
                author = "UNKNOWN"
            version = metadata.get_version()
            product_version = self.get_product_version()
            product_name = self.get_product_name()
            self.db = msilib.init_database(
                installer_name,
                msilib.schema,
                product_name,
                msilib.gen_uuid(),
                product_version,
                author)

            # Add tables
            msilib.add_tables(self.db, msilib.sequence)

            # Add meta-data
            props = [('DistVersion', version)]
            email = metadata.author_email or metadata.maintainer_email
            if email:
                props.append(("ARPCONTACT", email))
            if metadata.url:
                props.append(("ARPURLINFOABOUT", metadata.url))
            if props:
                msilib.add_data(self.db, 'Property', props)

            # Add sections
            self.add_find_python()
            self.add_files()
            self.add_scripts()
            self.add_ui()

            # Write the file and append to distribution's .dist_files
            self.db.Commit()
            if hasattr(self.distribution, 'dist_files'):
                self.distribution.dist_files.append(
                    ('bdist_msi', self.target_version, fullname))

            # Cleanup
            if not self.keep_temp:
                remove_tree(self.bdist_dir, dry_run=self.dry_run)

        def get_installer_filename(self, fullname):

            return os.path.join(self.dist_dir,
                                "%s.%s.msi" %
                                (fullname,
                                 self.plat_name))

else:
    
    class mx_bdist_msi:
        pass

if 0:
    # Hack to allow quick debugging of the mx_bdist_msi command
    if os.name == 'nt' and bdist_msi is None:
        raise TypeError('just testing...')

###

if setuptools is not None:

    from setuptools.command import egg_info
    from distutils.filelist import FileList

    class mx_egg_info(egg_info.egg_info):

        def find_sources(self):
            
            """ This method is used to generate the SOURCES.txt
                manifest file in the EGG-INFO directory.

                Since there's no clear use of that file and it
                prevents building eggs from prebuilt binaries, we'll
                just return a list with the EGG-INFO files.

            """
            self.filelist = FileList()
            egg_info = self.get_finalized_command('egg_info')
            self.filelist.include_pattern('*',
                                          prefix=egg_info.egg_info)

else:
    mx_egg_info = None

### Helpers to allow rebasing packages within setup.py files

def rebase_packages(packages, new_base_package, filter=None):

    rebased_packages = []
    for package in packages:
        # Apply filter (only rebase packages for which the filter
        # returns true)
        if (filter is not None and
            not filter(package)):
            rebased_packages.append(package)
        else:
            # Rebase the package
            rebased_packages.append(new_base_package + '.' + package)
    return rebased_packages

def rebase_files(files, new_base_dir, filter=None):

    rebased_files = []
    for file in files:
        # Apply filter (only rebase packages for which the filter
        # returns true)
        if (filter is not None and
            not filter(file)):
            rebased_files.append(file)
        else:
            # Rebase the file
            rebased_files.append(os.path.join(new_base_dir, file))
    return rebased_files

def rebase_extensions(extensions,
                      new_base_package, new_base_dir,
                      filter_packages=None, filter_files=None):

    rebased_extensions = []
    for ext in extensions:

        # Apply package filter to the extension name
        if (filter_packages is not None and
            not filter_packages(ext)):
            rebased_extensions.append(ext)
            continue

        # Create a shallow copy
        new_ext = copy.copy(ext)
        rebased_extensions.append(new_ext)

        # Standard distutils Extension
        new_ext.name = new_base_package + '.' + ext.name
        new_ext.sources = rebase_files(
            ext.sources,
            new_base_dir,
            filter_files)
        new_ext.include_dirs = rebase_files(
            ext.include_dirs,
            new_base_dir,
            filter_files)
        new_ext.library_dirs = rebase_files(
            ext.library_dirs,
            new_base_dir,
            filter_files)
        new_ext.runtime_library_dirs = rebase_files(
            ext.runtime_library_dirs,
            new_base_dir,
            filter_files)
        if not isinstance(ext, mx_Extension):
            continue

        # mx_Extension
        new_ext.data_files = rebase_files(
            ext.data_files,
            new_base_dir,
            filter_files)
        new_ext.packages = rebase_packages(
            ext.packages,
            new_base_package,
            filter_packages)

        if 0:
            # optional_libraries will not need any rebasing, since
            # the header files rely on the standard search path
            new_optional_libraries = []
            for (libname, header_files) in ext.optional_libraries:
                new_optional_libraries.append(
                    (libname,
                     rebase_files(header_files,
                                  new_base_dir,
                                  filter_files)))
            new_ext.optional_libraries = new_optional_libraries

        new_needed_includes = []
        for (filename, dirs, pattern) in ext.needed_includes:
            new_needed_includes.append(
                (filename,
                 rebase_files(dirs,
                              new_base_dir,
                              filter_files),
                 pattern))
        new_ext.needed_includes = new_needed_includes

        new_needed_libraries = []
        for (filename, dirs, pattern) in ext.needed_libraries:
            new_needed_libraries.append(
                (filename,
                 rebase_files(dirs,
                              new_base_dir,
                              filter_files),
                 pattern))
        new_ext.needed_libraries = new_needed_libraries

    return rebased_extensions
    
###

def run_setup(configurations):

    """ Run distutils setup.

        The parameters passed to setup() are extracted from the list
        of modules, classes or instances given in configurations.

        Names with leading underscore are removed from the parameters.
        Parameters which are not strings, lists or tuples are removed
        as well.  Configurations which occur later in the
        configurations list override settings of configurations
        earlier in the list.

    """
    # Build parameter dictionary
    kws = {
        # Defaults for distutils and our add-ons
        #'version': '0.0.0',
        #'name': '',
        #'description': '',
        'license': ('(c) eGenix.com Sofware, Skills and Services GmbH, '
                    'All Rights Reserved.'),
        'author': 'eGenix.com Software, Skills and Services GmbH',
        'author_email': 'info@egenix.com',
        'maintainer': 'eGenix.com Software, Skills and Services GmbH',
        'maintainer_email': 'info@egenix.com',
        'url': 'http://www.egenix.com/',
        'download_url': 'http://www.egenix.com/',
        'platforms': [],
        'classifiers': [],
        'packages': [],
        'ext_modules': [],
        'data_files': [],
        'libraries': [],
    }
    if setuptools is not None:
        # Add defaults for setuptools
        kws.update({
            # Default to not install eggs as ZIP archives
            'zip_safe': 0,
            })
    for configuration in configurations:
        kws.update(vars(configuration))

    # Type and name checking
    for name, value in kws.items():
        if (name[:1] == '_' or
            name in UNSUPPORTED_SETUP_KEYWORDS):
            del kws[name]
            continue
        if not isinstance(value, ALLOWED_SETUP_TYPES):
            if isinstance(value, types.UnicodeType):
                # Convert Unicode values to UTF-8 encoded strings
                kws[name] = value.encode('utf-8')
            else:
                del kws[name]
            continue
        #if type(value) is types.FunctionType:
        #    kws[name] = value()

    # Add setup extensions
    kws['distclass'] = mx_Distribution
    extensions = {'build': mx_build,
                  'build_unixlib': mx_build_unixlib,
                  'mx_autoconf': mx_autoconf,
                  'build_ext': mx_build_ext,
                  'build_clib': mx_build_clib,
                  'build_py': mx_build_py,
                  'build_data': mx_build_data,
                  'install': mx_install,
                  'install_data': mx_install_data,
                  'install_lib': mx_install_lib,
                  'uninstall': mx_uninstall,
                  'register': mx_register,
                  'bdist': mx_bdist,
                  'bdist_rpm': mx_bdist_rpm,
                  'bdist_zope': mx_bdist_zope,
                  'bdist_inplace': mx_bdist_inplace,
                  'bdist_wininst': mx_bdist_wininst,
                  'bdist_msi': mx_bdist_msi,
                  'bdist_prebuilt': mx_bdist_prebuilt,
                  'mx_bdist_egg': mx_bdist_egg,
                  'sdist': mx_sdist,
                  'clean': mx_clean,
                  }
    if bdist_ppm is not None:
        extensions['bdist_ppm'] = bdist_ppm.bdist_ppm
    if GenPPD is not None:
        extensions['GenPPD'] = GenPPD.GenPPD
    if mx_egg_info is not None:
        extensions['egg_info'] = mx_egg_info
    if setuptools is None:
        extensions['bdist_egg'] = mx_bdist_egg
        
    kws['cmdclass'] = extensions

    # Invoke distutils setup
    apply(setup, (), kws)

