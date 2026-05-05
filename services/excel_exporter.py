"""Excel export engine using pandas + openpyxl."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


class ExcelExporter:
    """Export selected document fields into an Excel worksheet."""

    def export_row(
        self,
        output_path: Path,
        selected_columns: list[dict],
        detected_map: dict[str, str],
        document_name: str,
    ) -> Path:
        row: dict[str, str] = {"document_name": document_name}

        for col in selected_columns:
            col_name = col.get("column_name", "").strip() or col.get("field_name", "")
            field_name = col.get("field_name", "")
            row[col_name] = detected_map.get(field_name, "")

        if output_path.exists():
            existing = pd.read_excel(output_path)
            for key in row.keys():
                if key not in existing.columns:
                    existing[key] = ""
            for key in existing.columns:
                if key not in row:
                    row[key] = ""
            df = pd.concat([existing, pd.DataFrame([row])[existing.columns]], ignore_index=True)
        else:
            df = pd.DataFrame([row])

        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(output_path, index=False, engine="openpyxl")
        return output_path
