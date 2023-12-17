#!/usr/bin/env python3

# @todo: Maybe remove glob2, as glob now (Python 3.5+) does `**/` matching.

import argparse
import boto3
import datetime
import glob2
import io
import json
import os
import yaml
import zipfile

from functools import reduce


def load(path, names=None):
	exclude = lambda key: key.startswith("_") or (names and key not in names)
	return {key: value for key, value in yaml.safe_load(open(path, "r")).items() if not exclude(key)}


def paths(patterns, root=""):
	globbed = [glob2.glob(os.path.join(root, pattern), include_hidden=True) for pattern in patterns]
	return [path for paths in globbed for path in paths if not os.path.isdir(path)]


def bundle(includes, excludes):
	bundled = io.BytesIO()
	excluded = set(paths(excludes))
	with zipfile.ZipFile(bundled, "w") as zipped:
		for root in includes:
			for path in set(paths(includes[root], root)) - excluded:
				zipped.write(path, os.path.relpath(path, root))
	return bundled


def just_lambdo_it():

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

	config = load(args.config, args.names)

	if args.print:
		return print(json.dumps(config, indent=2, sort_keys=True))

	# Retrieve a list of existing functions names:
	client = boto3.client("lambda")
	functions = [function["FunctionName"] for function in client.list_functions()["Functions"]]

	for name, options in config.items():

		if args.deploy:
			package = bundle(options["includes"], options.get("excludes", [])).getvalue()
			params = {
				"FunctionName": name,
				"Role":         options["role"],
				"Runtime":      options["runtime"],
				"Handler":      options["handler"],
				"Layers":       options.get("layers", []),
				"Timeout":      options.get("timeout", 3), # 3 seconds = AWS Lambda default.
				"MemorySize":   options.get("memory", 128), # 128 MB = AWS Lambda default.
				"Environment":  {"Variables": options.get("env", {})}
			}
			if name in functions:
				response = client.update_function_configuration(**params)

				# @todo: Wait for function state "InProgress" to pass here.
				# @debug:
				print(response["State"], response["StateReason"])

				client.update_function_code(FunctionName=name, ZipFile=package)
				print(f"Updated function: {name}")
			else:
				client.create_function(**params, Code={"ZipFile": package})
				# @todo: Wait for function state "Pending" to pass here.
				print(f"Created function: \x1b[1;32m{name}\x1b[0m")

		if args.version:
			description = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
			version = client.publish_version(FunctionName=name, Description=description)["Version"]
			print(f"Published function version: \x1b[1;32m{name}:{version}\x1b[0m")

		if args.alias:
			versions = [
				version["Version"]
				for version in client.list_versions_by_function(FunctionName=name)["Versions"]
			]
			version = (
				"$LATEST"
				if args.latest
				else sorted(versions, key=lambda i: i.zfill(9) if i.isnumeric() else i)[-1]
			)
			params = {
				"Name": args.alias,
				"FunctionName": name,
				"FunctionVersion": version
			}
			aliases = [alias["Name"] for alias in client.list_aliases(FunctionName=name)["Aliases"]]
			if args.alias in aliases:
				client.update_alias(**params)
				print(f"Updated function alias: {name}:\x1b[1;34m{args.alias}\x1b[0m → ~:{version}")
			else:
				client.create_alias(**params)
				print(f"Created function alias: \x1b[1;32m{name}\x1b[0m:\x1b[1;34m{args.alias}\x1b[0m → ~:{version}")


yaml.SafeLoader.add_constructor("!env", lambda loader, node: os.getenv(node.value, ""))
yaml.SafeLoader.add_constructor("!join", lambda loader, node: "".join([str(i) for i in loader.construct_sequence(node)]))

if __name__ == "__main__":
	just_lambdo_it()
