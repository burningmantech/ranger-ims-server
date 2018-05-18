extensions = ["sphinx.ext.autodoc"]

# Project info

project = "ranger-ims-server"
copyright = "2016-2018"
author = "Wilfredo S\xe1nchez Vega"

# File names

templates_path = []
html_static_path = []
source_suffix = [".rst", ".md"]
master_doc = "index"
exclude_patterns = []

# Styling

html_theme = "sphinx_rtd_theme"

# Pedantry

nitpicky = True
nitpick_ignore = [
    # Bugs in Python documentation
    ("py:class", "float"     ),
    ("py:class", "int"       ),
    ("py:class", "object"    ),
    ("py:class", "Union"     ),
    ("py:data" , "sys.argv"  ),
    ("py:exc"  , "ValueError"),
    ("py:obj"  , "None"      ),

    # Need to learn how to intersphinx with Twisted
    ("py:class", "twisted.internet.defer.Deferred"                           ),
    ("py:class", "twisted.trial._synctest.SynchronousTestCase"               ),
    ("py:class", "twisted.trial.unittest.SynchronousTestCase"                ),
    ("py:class", "twisted.trial.unittest.TestCase"                           ),
    ("py:const", "twisted.web.http.NOT_FOUND"                                ),
    ("py:meth" , "twisted.trial.unittest.SynchronousTestCase.successResultOf"),
    ("py:mod"  , "twisted.trial.unittest"                                    ),

    # Need to learn how to intersphinx with Klein
    ("py:class", "klein.app.Klein"),
]
