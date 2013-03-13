from setuptools import setup, find_packages
setup(
    name = "fsm",
    version = "0.1",
    packages = find_packages(),
    scripts = [],

    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    install_requires = ['flask', 'SQLAlchemy', 'python-dateutil==1.5', "lxml", "python-slugify"],

#    package_data = {
        # If any package contains *.txt or *.rst files, include them:
#        '': ['*.txt', '*.rst'],
        # And include any *.msg files found in the 'hello' package, too:
#        'hello': ['*.msg'],
#    }

    # metadata for upload to PyPI
    author = "Yiming Liu",
    author_email = "pertinax+fsm@gmail.com",
    description = "FSM reference implementation",
    license = "BSD",
    keywords = "FSM, AtomPub",
    url = "http://people.ischool.berkeley.edu/~yliu/fsm",   # project home page, if any

    # could also include long_description, download_url, classifiers, etc.
)
