import inspect

from setuptools import setup


# reStructuredText:
description = """
	Humor is the only test of gravity, and gravity of humor; for a subject which
	will not bear raillery is suspicious, and a jest which will not bear serious
	examination is false wit.
	"""

# @todo: Add more and better package meta data and description for PyPI.
setup(
	name="lambdo",
	description="Just lambdo it",
	long_description=inspect.cleandoc(description),
	author="Jan van Hellemond",
	author_email="jvhellemond@gmail.com",
	url="https://github.com/jvhellemond/lambdo",
	version="5.8.3",
	install_requires=["boto3", "glob2", "PyYAML"],
	py_modules=["lambdo"],
	entry_points={"console_scripts": ["lambdo=lambdo:just_lambdo_it"]}
)
