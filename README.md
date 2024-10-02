# uv-pyo3

Cross platform (windows & linux) example of how to use [pyo3](https://pyo3.rs/) to embed a python interpreter into rust, 
with the interpreter and venv provided by [uv](https://docs.astral.sh/uv/).

Requires [cargo](https://doc.rust-lang.org/cargo/getting-started/installation.html) and [uv](https://docs.astral.sh/uv/getting-started/installation/) installed.

Most of the "magic" is in `build.py`, which is a wrapper around cargo. This can be executed directly with python >= 3.9, but I would recommend using `uv run build.py`,
so that the python environment is automatically set up by uv, since this will be needed to run the project in any case.

In order to run the provided example of generating a [polars](https://pola.rs/) DataFrame in rust and passing it to python for charting, run `uv run build.py run` 
which will setup the everything needed for pyo3, mostly environment variables pointing at the python instance managed by uv, as well as a pyo3 config file pointing to the same instance of python,
and then execute `cargo run`.

Note this will fail if run in wsl when attemping to open the html file containing the chart. (see [python bug](https://github.com/python/cpython/issues/89752))

We use the dynamically embedded route described in the [pyo3 guide](https://pyo3.rs/main/building-and-distribution#dynamically-embedding-the-python-interpreter)
This means we need a python interpreter available at runtime, on the dylib path.
The rust executable (`main.rs`) also has the path to the virtual environment hardcoded into the binary.
All this means this approach is probably suitable for somewhat technical users that have your code checked out on their machine, rather than as something distributable.

