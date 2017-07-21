import os, sys, subprocess
from setuptools import setup, find_packages
from distutils import log
from distutils.command.build import build as _build
from setuptools.command.install import install as _install
from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
from distutils.errors import DistutilsSetupError
from codecs import open

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

builddir = None
def get_builddir():
    global builddir
    if builddir is None:
        topdir = os.getcwd()
        builddir = os.path.join(topdir, 'builddir')
    return builddir

srcdir = None
def get_srcdir():
    global srcdir
    if srcdir is None:
        topdir = os.getcwd()
        srcdir = os.path.join(topdir, 'src')
    return srcdir

prefix = None
def get_prefix():
    global prefix
    if prefix is None:
        prefix = os.path.join(get_builddir(), 'install', 'cppyy_backend')
    return prefix


class my_cmake_build(_build):
    def run(self):
        # base run
        _build.run(self)

        # custom run
        log.info('Now building libcppyy_backend.so and dependencies')
        builddir = get_builddir()
        prefix   = get_prefix()
        srcdir   = get_srcdir()
        if not os.path.exists(builddir):
            log.info('Creating build directory %s ...' % builddir)
            os.makedirs(builddir)

        olddir = os.getcwd()
        os.chdir(builddir)
        log.info('Running cmake for cppyy_backend')
        if subprocess.call([
                'cmake', srcdir, '-Dminimal=ON -Dasimage=OFF',
                '-DCMAKE_INSTALL_PREFIX='+prefix]) != 0:
            os.chdir(olddir)
            raise DistutilsSetupError('Failed to configure cppyy_backend')

        nprocs = os.getenv("MAKE_NPROCS")
        if nprocs:
            try:
                ival = int(nprocs)
                nprocs = '-j'+nprocs
            except ValueError:
                log.warn("Integer expected for MAKE_NPROCS, but got %s (ignored)", nprocs)
                nprocs = '-j1'
        else:
            nprocs = '-j1'
        log.info('Now building cppyy_backend and dependencies ...')
        if subprocess.call(['make', nprocs]) != 0:
            raise DistutilsSetupError('Failed to build cppyy_backend')

        os.chdir(olddir)
        log.info('build finished')

class my_install(_install):
    def _get_install_path(self):
        # depending on goal, copy over pre-installed tree
        if hasattr(self, 'bdist_dir') and self.bdist_dir:
            install_path = self.bdist_dir
        else:
            install_path = self.install_lib
        return install_path

    def run(self):
        # base install
        _install.run(self)

        # custom install of backend
        log.info('Now installing libcppyy_backend.so and dependencies')
        builddir = get_builddir()
        if not os.path.exists(builddir):
            raise DistutilsSetupError('Failed to find build dir!')
        olddir = os.getcwd()
        os.chdir(builddir)

        prefix = get_prefix()
        log.info('Now creating installation under %s ...', prefix)
        if subprocess.call(['make', 'install']) != 0:
            os.chdir(olddir)
            raise DistutilsSetupError('Failed to install cppyy_backend')

        os.chdir(olddir)
        prefix_base = os.path.join(get_prefix(), os.path.pardir)
        install_path = self._get_install_path()
        log.info('Copying installation to: %s ...', install_path)
        self.copy_tree(prefix_base, install_path)

        log.info('install finished')

    def get_outputs(self):
        outputs = _install.get_outputs(self)
        outputs.append(os.path.join(self._get_install_path(), 'cppyy_backend'))
        return outputs

class my_bdist_wheel(_bdist_wheel):
    def finalize_options(self):
     # this is a universal, but platform-specific package; a combination
     # that wheel does not recognize, thus simply fool it
        from distutils.util import get_platform
        self.plat_name = get_platform()
        _bdist_wheel.finalize_options(self)


setup(
    name='cppyy-backend',
    description='cppyy backend containing Cling/LLVM',
    long_description=long_description,
    url='http://pypy.org',

    # Author details
    author='PyPy Developers',
    author_email='pypy-dev@python.org',

    use_scm_version=True,
    setup_requires=['setuptools_scm'],

    license='LLVM: UoI-NCSA; ROOT: LGPL 2.1; Cppyy: LBNL BSD',

    classifiers=[
        'Development Status :: 4 - Beta',

        'Intended Audience :: Developers',

        'Topic :: Software Development',
        'Topic :: Software Development :: Interpreters',

        #'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: C',
        'Programming Language :: C++',

        'Natural Language :: English'
    ],

    keywords='interpreter development, C++ bindings',

    include_package_data=True,

    package_dir={'': 'src'},
    packages=find_packages('src', include=['cppyy_backend']),

    cmdclass = {
        'build': my_cmake_build,
        'install': my_install,
        'bdist_wheel': my_bdist_wheel,
    },

    entry_points={
        "console_scripts": [
            "genreflex = cppyy_backend._genreflex:main",
        ],
    },
)
