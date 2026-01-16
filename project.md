# Supypowers

1. What is a superpower?

Supypowers are essentially tools for LLMs, we want to create a library of functions that:

- are self contained within a python script
- can be executed using a CLI
- don't require a server to be open

A superpower is a python script that has the following properties:

- One (or more functions) that accept a documented set of inputs (validated using a serialization library such as Pydantic)
- Validated and documented set of outputs
- It can be run without any venv being defined using uv's dependencies

for example, in examples/exponents.py we have an example of how I want these functions to look like.

2. What do we need to build?

a) a CLI like

`supypowers run <folder_name> <script>:<function> <input_json> --secrets <env_file_or_secrets>`

`supypowers run examples exponents:compute_sqrt "{a:1}" ` which executes the function in the script. It should use uv's dependencies using uv's scripts framework

b) a way to get the documentation out of every function that's accessible within the folder.. essentially I want a context to pass to the LLM. Each function should come with:

- function name
- function description
- input schema
- (optional) output schema or any

b) possible decorators that need to go into the scripts to make life simpler (like defining requirements, defining documentations, etc)
