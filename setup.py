from setuptools import setup

setup(
	name="deployer",
	description="Deployie McDeployface",
	version="2.9",
	install_requires=["boto3", "glob2", "PyYAML"],
	py_modules=["deployer"],
	entry_points={"console_scripts": ["deploy=deployer:deploy"]}
)
