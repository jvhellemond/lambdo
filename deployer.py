#!/usr/bin/env python3

import argparse
import boto3
import glob2
import io
import os
import yaml
import zipfile


def paths(patterns, root=""):
	globbed = [glob2.glob(
		os.path.join(root, pattern),
		include_hidden=True
	) for pattern in patterns]
	return [path for paths in globbed for path in paths if not os.path.isdir(path)]


def package(includes, excludes):
	zipped = io.BytesIO()
	excluded = paths(excludes)
	with zipfile.ZipFile(zipped, "w") as compressed:
		for root in includes:
			for path in sorted(set(paths(includes[root], root)) - set(excluded)):
				compressed.write(path, os.path.relpath(path, root))
	return zipped


def deploy():

	# Parse arguments:
	parser = argparse.ArgumentParser(add_help=False)
	parser.add_argument("-c", "--config", default="deploy.yaml")
	parser.add_argument("-n", "--name")
	parser.add_argument("-d", "--dryrun", dest="dryrun", action="store_true")
	parser.add_argument("-h", "--help")
	args = parser.parse_args()

	config = yaml.safe_load(open(args.config, "r"))
	exclude = lambda key: key.startswith("_") or (args.name and args.name != key)
	functions = {key: value for key, value in config.items() if not exclude(key)}

	# Retrieve a list of existing functions names:
	lambda_ = boto3.client("lambda")
	functions_ = lambda_.list_functions()["Functions"]
	existing = [function["FunctionName"] for function in functions_]

	for name, function in functions.items():

		code = package(
			function["includes"],
			function.get("excludes", [])
		).getvalue()

		if args.dryrun:
			print(f"📦 \x1b[2m{name}\x1b[0m")
		elif name not in existing:
			lambda_.create_function(
				FunctionName=name,
				Role=function["role"],
				Runtime=function["runtime"],
				Handler=function["handler"],
				Environment={"Variables": function.get("env", {})},
				Layers=function.get("layers", []),
				Timeout=function.get("timeout", 3), # Lambda default timeout is 3 seconds.
				MemorySize=function.get("memory", 128), # Lambda default memory size is 128 MB.
				Code={"ZipFile": code}
			)
			print(f"🦄 \x1b[1;32m{name}\x1b[0m")
		else:
			lambda_.update_function_configuration(
				FunctionName=name,
				Role=function["role"],
				Runtime=function["runtime"],
				Handler=function["handler"],
				Environment={"Variables": function.get("env", {})},
				Layers=function.get("layers", []),
				Timeout=function.get("timeout", 3), # Lambda default timeout is 3 seconds.
				MemorySize=function.get("memory", 128), # Lambda default memory size is 128 MB.
			)
			lambda_.update_function_code(
				FunctionName=name,
				ZipFile=code
			)
			print(f"🦄 {name}")


yaml.SafeLoader.add_constructor(
	"!include",
	lambda loader, node: yaml.safe_load(
		open(os.path.join(os.path.dirname(loader.name), node.value), "r")
	)
)

if __name__ == "__main__":
	deploy()
