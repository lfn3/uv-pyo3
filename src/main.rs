use std::path::PathBuf;

use polars::df;
use pyo3::{
    types::{PyAnyMethods, PyList, PyListMethods, PyModule},
    Py, PyAny, PyResult, Python,
};
use pyo3_polars::PyDataFrame;

const HELLO_PY: &str = include_str!("../hello.py");

#[cfg(target_os = "windows")]
fn venv_packages_dir() -> PathBuf {
    ".venv\\Lib\\site-packages".into()
}

#[cfg(target_os = "linux")]
fn venv_packages_dir() -> PathBuf {
    ".venv/lib/python3.12/site-packages/".into()
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let df = df!("Date" => ["2024-10-01", "2024-10-02", "2024-10-03"],
                            "Value" => [1, 2, 4])?;

    pyo3::prepare_freethreaded_python();
    let venv_lib_dir = venv_packages_dir();

    let from_python = Python::with_gil(|py| -> PyResult<Py<PyAny>> {
        // Add the venv to the path (https://docs.python.org/3/library/sys_path_init.html)
        let syspath = py
            .import_bound("sys")?
            .getattr("path")?
            .downcast_into::<PyList>()?;
        syspath.insert(0, venv_lib_dir)?;
        let hello_mod = PyModule::from_code_bound(py, HELLO_PY, "hello.py", "hello")?;
        let hello_line_graph: Py<PyAny> = hello_mod.getattr("line_graph")?.into();

        let args = (PyDataFrame(df), "Date", "Value");

        hello_line_graph.call1(py, args)
    });

    println!("{from_python:?}");

    Ok(())
}
