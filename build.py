import os
from pathlib import Path
import platform
import re
import subprocess
import sys

# https://doc.rust-lang.org/cargo/reference/environment-variables.html#dynamic-library-paths
# https://stackoverflow.com/a/53215943
SYSTEM_TO_DYLIB_ENVVAR = {
    "Linux": "LD_LIBRARY_PATH",
    "Windows": "PATH",
    "Darwin": "DYLD_FALLBACK_LIBRARY_PATH",
}

PYO3_PRINT_PREFIX = (
    "  -- PYO3_PRINT_CONFIG=1 is set, printing configuration and halting compile --\n"
)
PYO3_PRINT_SUFFIX = "note: unset the PYO3_PRINT_CONFIG environment variable and retry to compile with the above config"


def find_matching_python_verions(uv_python_list: str, version: str) -> list[str]:
    """ Parses the provided output of `uv python list` to find paths to matching python versions """
    pat_str = f"^\\S+-{version}\\.\\d+-\\S+\\s+(\\S+-{version}\\.\\d+-\\S+)"
    pat = re.compile(pat_str, flags=re.MULTILINE)
    matches = pat.findall(uv_python_list)

    return matches


def python_exec_path() -> Path:
    """ Finds the path to a python executable managed by uv using the .python-version file and a call to `uv python list` """
    with open(".python-version", "r") as f:
        version = f.read().removesuffix("\n")

    pythons = subprocess.run(["uv", "python", "list"], capture_output=True)
    pythons_out = pythons.stdout.decode()
    matches = find_matching_python_verions(pythons_out, version)
    assert len(matches) == 1, "Expected only a single matching toolchain"

    return Path(matches[0])


def python_dylib_dir(exec_path: Path) -> Path:
    """ Given the path to a python executable managed by uv, gives the path to the dylib directory """
    system = platform.system()

    if system == "Linux":
        return Path(exec_path).parent.parent / "lib"
    elif system == "Windows":
        return Path.home() / Path(exec_path).parent / "libs"
    else:
        raise ValueError(
            "Don't know how to build a dylib path for `platform.system()`: '{system}'"
        )


def find_python_lib_paths(exec_path: Path) -> list[Path]:
    """ Given the path to a python executable managed by uv, gives the path to the lib dirs needed to compile pyo3 """
    system = platform.system()
    dylib_dir = python_dylib_dir(exec_path)

    if system == "Linux":
        return [dylib_dir]
    elif system == "Windows":
        return [dylib_dir, dylib_dir.parent]
    else:
        raise ValueError(
            "Don't know how to build a library path for `platform.system()`: '{system}'"
        )


def pyo3_config_path() -> Path:
    return Path(os.getcwd()) / "pyo3_config"


def ensure_pyo3_config(env: dict, python_exec_path: Path, verbose: bool):
    """ Generate a pyo3 config from the default config with the dylib path replaced by the path to a uv managed python dylib dir """
    path = pyo3_config_path()        
    if not path.exists():

        env = env.copy()
        env["PYO3_PRINT_CONFIG"] = "1"

        build_output_with_pyo3_config = subprocess.run(
            ["cargo", "build"], env=env, capture_output=True
        ).stderr.decode()

        from_idx = build_output_with_pyo3_config.find(PYO3_PRINT_PREFIX)
        if from_idx == -1:
            raise ValueError("Could not find pyo3 config in build stderr output")
        from_idx = from_idx + len(PYO3_PRINT_PREFIX)
        to_idx = build_output_with_pyo3_config.find(PYO3_PRINT_SUFFIX, from_idx)
        pyo3_config = build_output_with_pyo3_config[from_idx:to_idx]

        rebuilt = []
        for line in pyo3_config.splitlines():
            line = line.strip()
            if line.startswith("lib_dir="):
                python_lib_path = str(python_dylib_dir(python_exec_path))
                rebuilt.append(f"lib_dir={python_lib_path}")
            elif len(line) > 0:
                rebuilt.append(line)

        with path.open(mode="w+t") as f:
            f.write("\n".join(rebuilt))

        if verbose:
            print(f"Wrote pyo3 config to {path}")
    elif verbose:
        print(f"{path} already exists, skipping write of pyo3 config")


def extend_env_with_python_dylib(env: dict, exec_path: Path, verbose: bool) -> dict:
    """ Extend the os specific dylib path var with the path to a python interpreter lib """
    env = env.copy()
    system = platform.system()

    amend = SYSTEM_TO_DYLIB_ENVVAR.get(system)
    if amend is None:
        raise ValueError("Unknown value of `platform.system()`: '{system}'")

    paths = find_python_lib_paths(exec_path)

    paths_str = os.pathsep.join([str(p) for p in paths])

    if verbose:
        print(f"Adding {paths_str} to {amend}")

    if amend in env:
        env[amend] += paths_str
    else:
        env[amend] = paths_str

    return env


def main():
    exec_path = python_exec_path()
    args = sys.argv[1:]

    verbose = any(a == '-v' or a == '--verbose' for a in args)

    env = os.environ
    
    ensure_pyo3_config(env, exec_path, verbose)

    env["PYO3_CONFIG_FILE"] = str(pyo3_config_path())

    env = extend_env_with_python_dylib(env, exec_path, verbose)

    subprocess.run(["cargo", *sys.argv[1:]], env=env)


if __name__ == "__main__":
    main()


def test_find_matching_python_verion_linux():
    assert find_matching_python_verions(
        "cpython-3.12.6-linux-x86_64-gnu       /home/bob/.local/share/uv/python/cpython-3.12.6-linux-x86_64-gnu/bin/python3 -> python3.12",
        "3.12",
    ) == [
        "/home/bob/.local/share/uv/python/cpython-3.12.6-linux-x86_64-gnu/bin/python3"
    ]

def test_find_matching_python_version_linux_no_path():
    assert (
        find_matching_python_verions(
            "cpython-3.12.6-linux-x86_64-gnu       <download available>",
            "3.12",
        )
        == []
    )

def test_find_matching_python_version_windows():
    assert find_matching_python_verions(
        "cpython-3.12.6-windows-x86_64-none       AppData\\Roaming\\uv\\python\\cpython-3.12.6-windows-x86_64-none\\python.exe",
        "3.12",
    ) == [
        "AppData\\Roaming\\uv\\python\\cpython-3.12.6-windows-x86_64-none\\python.exe"
    ]

def test_find_matching_python_version_windows_no_path():
    assert (
        find_matching_python_verions(
            "cpython-3.12.6-windows-x86_64-none       <download available>",
            "3.12",
        )
        == []
    )