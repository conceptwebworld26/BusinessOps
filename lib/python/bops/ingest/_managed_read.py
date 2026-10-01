"""Worker executed inside the managed runtime to read a workbook with openpyxl (Tier 2).

Run as a subprocess by `readers.read_xlsx_managed`, never imported in-process. It exists as
a real module rather than an embedded script string so it can be read, linted and tested
like any other code.

    python _managed_read.py <engine_root> <workbook path> [sheet name]

Emits one JSON object on stdout. Reads only; writes nothing.
"""

import json
import sys


def main(argv):
    engine_root, path = argv[0], argv[1]
    sheet = argv[2] if len(argv) > 2 else None

    sys.path.insert(0, engine_root)
    from bops.ingest import readers

    dataset = readers.read_xlsx_openpyxl(path, sheet)
    json.dump({
        "columns": dataset.columns,
        "rows": dataset.rows,
        "sheet": dataset.sheet,
        "sheets": dataset.sheets,
        "warnings": [w.as_dict() for w in dataset.warnings],
    }, sys.stdout, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
