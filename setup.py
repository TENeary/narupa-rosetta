
# Licensed under the GPL. See License.txt in the project root for license information.
#!/usr/bin/env python

from distutils.core import setup
from setuptools import find_namespace_packages

setup(
    name="narupa-rosetta",
    version="0.0.0",
    description="Rosetta interface methods for Narupa",
    author="Intangible Realities Lab",
    author_email="tn15550@bristol.ac.uk",
    url="https://gitlab.com/intangiblerealities/",
    packages=find_namespace_packages("src", include="narupa.*"),
    package_dir={"": "src"},
    install_requires=(
        "narupa",
        "pyzmq",
    ),
)