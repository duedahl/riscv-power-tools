# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os, sys
sys.path.insert(0, os.path.abspath('../../chipwhisperer/jupyter/Data_Generation_Pipeline'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'riscv-power-tools'
copyright = '2025, Mathias Duedahl'
author = 'Mathias Duedahl'
release = 'v0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',       # Auto-document docstrings
    'sphinx.ext.napoleon',      # Support Google-style docstrings
    'sphinx.ext.autosummary',   # Optionally generate summaries for your modules
    'nbsphinx',                 # To include Jupyter notebooks
    'sphinx_autodoc_typehints', # For automatic type hint documentation
]

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False

autodoc_default_options = {
    'members': True,             # Include methods and functions in the doc
    'undoc-members': True,       # Include undocumented members (if any)
    'private-members': True,     # Include private members (e.g., _foo)
    'show-inheritance': True,    # Show class inheritance
    'exclude-members': '__weakref__',  # Optionally exclude weakref from the docs
}

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
