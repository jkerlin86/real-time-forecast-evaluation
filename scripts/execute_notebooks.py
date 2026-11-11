"""Execute both notebooks in place with the project environment."""

from __future__ import annotations

from pathlib import Path

from nbclient import NotebookClient
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    for name in ["01_vintage_matrices_and_revisions.ipynb", "02_honest_vs_naive.ipynb"]:
        path = ROOT / "notebooks" / name
        nb = nbf.read(path, as_version=4)
        client = NotebookClient(
            nb, timeout=1200, kernel_name="python3", resources={"metadata": {"path": str(path.parent)}}
        )
        client.execute()
        nbf.write(nb, path)
        errors = [
            out
            for cell in nb.cells
            for out in cell.get("outputs", [])
            if out.get("output_type") == "error"
        ]
        print(name, "executed; error outputs:", len(errors))
        assert not errors, f"{name} has error outputs"


if __name__ == "__main__":
    main()
