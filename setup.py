from setuptools import setup

setup(
	name="lambdo",
	description="Just lambdo it",
	version="3.0",
	install_requires=["boto3", "glob2", "PyYAML"],
	py_modules=["lambdo"],
	entry_points={"console_scripts": ["lambdo=lambdo:main"]}
)
