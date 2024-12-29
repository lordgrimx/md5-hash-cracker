import os
import sys
sys.path.insert(0, os.path.abspath('../..'))

project = 'MD5 Hash Cracker'
copyright = '2024, Your Name'
author = 'Your Name'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

html_theme = 'sphinx_rtd_theme' 