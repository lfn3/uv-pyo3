from pathlib import Path
import tempfile
import webbrowser
import polars as pl


def line_graph(df: pl.DataFrame, x: str, y: str) -> Path:
    chart = df.plot.line(x=x, y=y)
    path = Path(tempfile.gettempdir()) / "chart.html"
    with path.open(mode="w+t") as f:
        f.write(chart.to_html())

    print(f"Wrote graph to {path}")

    webbrowser.open(str(path))
    
    return path
