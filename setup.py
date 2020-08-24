from setuptools import setup

# @todo: Add more package meta information for PyPI.
setup(
	name="lambdo",
	description="Just lambdo it",
	long_description="@todo: Write a long description, format it as reStructuredText",
	author="Jan van Hellemond",
	author_email="jvhellemond@gmail.com",
	url="https://github.com/jvhellemond/lambdo",
	version="5.7",
	install_requires=["boto3", "glob2", "PyYAML"],
	py_modules=["lambdo"],
	entry_points={"console_scripts": ["lambdo=lambdo:main"]}
)
