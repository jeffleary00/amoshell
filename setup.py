import os
from distutils.core import setup

contents = ""
if os.path.exists('README.rst'):
    readme = open('README.rst', 'r')
    contents = readme.read()
    
setup(
  name = 'amoshell',
  packages = ['amoshell'],
  version = '0.2',
  description = "Python interface to Ericsson's amos/moshell programs",
  long_description=contents,
  author = 'Jeff Leary',
  author_email = 'sillymonkeysoftware@gmail.com',
  url = 'https://github.com/jeffleary00/amoshell',
  download_url = 'https://github.com/jeffleary00/amoshell/tarball/0.1',
  classifiers = [
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
  ],
)
