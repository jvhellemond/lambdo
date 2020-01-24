#!/usr/bin/env python3

import argparse
import boto3
import datetime
import glob2
import io
import os
import yaml
import zipfile

from functools import reduce


def paths(patterns, root=""):
	globbed = [glob2.glob(
		os.path.join(root, pattern),
		include_hidden=True
	) for pattern in patterns]
	return [path for paths in globbed for path in paths if not os.path.isdir(path)]


def bundle(includes, excludes):
	bundled = io.BytesIO()
	excluded = set(paths(excludes))
	with zipfile.ZipFile(bundled, "w") as zipped:
		for root in includes:
			for path in set(paths(includes[root], root)) - excluded:
				zipped.write(path, os.path.relpath(path, root))
	return bundled


def main():

	# Parse arguments:
	parser = argparse.ArgumentParser(add_help=False)
	parser.add_argument("names", nargs="*")
	parser.add_argument("-c", "--config", default="lambdo.yaml")
	parser.add_argument("-p", "--print", dest="print", action="store_true")
	parser.add_argument("-d", "--deploy", dest="deploy", action="store_true")
	parser.add_argument("-v", "--version", dest="version", action="store_true")
	parser.add_argument("-a", "--alias", default=None)
	parser.add_argument("-l", "--latest", dest="latest", action="store_true")
	parser.add_argument("-h", "--help")
	args = parser.parse_args()

	config = yaml.safe_load(open(args.config, "r"))
	exclude = lambda key: key.startswith("_") or (args.names and key not in args.names)
	included = {key: value for key, value in config.items() if not exclude(key)}

	if args.print:
		return print(config)

	# Retrieve a list of existing functions names:
	client = boto3.client("lambda")
	functions = [function["FunctionName"] for function in client.list_functions()["Functions"]]

	for name, function in included.items():

		if args.deploy:
			package = bundle(function["includes"], function.get("excludes", [])).getvalue()
			params = {
				"FunctionName": name,
				"Role": function["role"],
				"Runtime": function["runtime"],
				"Handler": function["handler"],
				"Environment": {"Variables": function.get("env", {})},
				"Layers": function.get("layers", []),
				"Timeout": function.get("timeout", 3), # 3s = AWS Lambda default.
				"MemorySize": function.get("memory", 128) # 128MB = AWS Lambda default.
			}
			if name in functions:
				client.update_function_configuration(**params)
				client.update_function_code(FunctionName=name, ZipFile=package)
				print(f"🦄 {name}")
			else:
				client.create_function(**params, Code={"ZipFile": package})
				print(f"🦄 \x1b[1;32m{name}\x1b[0m")

		if args.version:
			version = client.publish_version(
				FunctionName=name,
				Description=datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
			)
			print(f"✨ {name}:\x1b[1;34m{version['Version']}\x1b[0m")

		if args.alias:
			versions = [int(version["Version"]) for version in client.list_versions_by_function(FunctionName=name)["Versions"]]
			version = "$LATEST" if args.latest else max(versions)
			aliases = [alias["Name"] for alias in client.list_aliases(FunctionName=name)["Aliases"]]
			params = {
				"Name": args.alias,
				"FunctionName": name,
				"FunctionVersion": version
			}
			if args.alias in aliases:
				client.update_alias(**params)
				print(f"🔗 {name}:\x1b[1;34m{args.alias}\x1b[0m → {name}:\x1b[1;34m{version}\x1b[0m")
			else:
				client.create_alias(**params)
				print(f"🔗 \x1b[1;32m{name}\x1b[0m:\x1b[1;34m{args.alias}\x1b[0m → {name}:\x1b[1;34m{version}\x1b[0m")


yaml.SafeLoader.add_constructor(
	"!env",
	lambda loader, node: os.getenv(node.value, "")
)

if __name__ == "__main__":
	main()
