"""
Stage 0 — Curado del Dataset CSIC 2010

Escanea y reporta PII encontrado en el dataset.
No modifica los datos — solo genera un reporte de hallazgos.

Uso:
    python -m src.mlsec.data.curate_dataset \
        --input data/raw/csic2010/csic_database.csv \
        --report data/curated/csic2010/curation_report.md
"""

import argparse
from pathlib import Path

import pandas as pd

# Columnas del CSV CSIC 2010
COLUMN_LABEL = "classification"
COLUMN_URL = "URL"

# Patrones de PII a buscar
PII_PATTERNS = {
    "session_token": {
        "columns": ["cookie"],
        "pattern": r"JSESSIONID=[A-Za-z0-9\-_]+",
        "description": "Session tokens JSESSIONID",
    },
    "phone": {
        "columns": ["content", "URL"],
        "pattern": r"\+?\d{1,4}[-\s]?\(?\d{1,4}\)?[-\s]?\d{1,4}[-\s]?\d{1,9}",
        "description": "Números de teléfono",
    },
    "email": {
        "columns": ["content", "URL", "User-Agent"],
        "pattern": r"[\w\.-]+@[\w\.-]+\.\w+",
        "description": "Direcciones de email",
    },
    "ip_address": {
        "columns": ["host", "URL"],
        "pattern": r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b",
        "description": "Direcciones IP",
    },
}

# Empresas/organizaciones a buscar
COMPANY_PATTERNS = [
    "hackademy",
    "ekoparty",
    "csic",
    "consejo superior de investigaciones científicas",
    "universidad de granada",
]


def scan_pii(df: pd.DataFrame) -> dict:
    """
    Escanea el dataset en busca de PII.

    Returns:
        dict con counts por tipo de PII y ejemplos
    """
    findings = {}

    for pii_type, config in PII_PATTERNS.items():
        total_count = 0
        examples = []

        for col in config["columns"]:
            if col not in df.columns:
                continue

            mask = df[col].astype(str).str.contains(config["pattern"], regex=True, na=False)
            count = mask.sum()
            total_count += count

            if count > 0 and len(examples) < 3:
                # Tomar ejemplos
                sample = df[mask][col].head(3).tolist()
                examples.extend([str(s)[:100] for s in sample])

        findings[pii_type] = {
            "count": total_count,
            "description": config["description"],
            "examples": examples[:3],
        }

    return findings


def check_company_references(df: pd.DataFrame) -> dict:
    """
    Busca referencias a empresas/organizaciones específicas.

    Returns:
        dict con resultados por empresa buscada
    """
    results = {}

    for company in COMPANY_PATTERNS:
        found = False
        columns_checked = []
        sample = None

        for col in df.columns:
            if df[col].dtype == object:
                mask = df[col].astype(str).str.lower().str.contains(company, na=False)
                if mask.any():
                    found = True
                    columns_checked.append(col)
                    sample = df[mask][col].head(1).tolist()

        results[company] = {
            "found": found,
            "columns": columns_checked,
            "sample": sample[0][:200] if sample else None,
        }

    return results


def analyze_class_balance(df: pd.DataFrame) -> dict:
    """Analiza distribución de clases."""
    df_temp = df.copy()
    df_temp[COLUMN_LABEL] = df_temp[COLUMN_LABEL].map({
        0: 0, "0": 0,
        1: 1, "1": 1
    })

    attack_count = (df_temp[COLUMN_LABEL] == 1).sum()
    normal_count = (df_temp[COLUMN_LABEL] == 0).sum()
    total = len(df)

    return {
        "normal": int(normal_count),
        "attack": int(attack_count),
        "total": int(total),
        "attack_rate": attack_count / total * 100,
        "normal_rate": normal_count / total * 100,
    }


def generate_report(
    input_path: str,
    pii_findings: dict,
    company_findings: dict,
    class_balance: dict,
    total_rows: int,
) -> str:
    """Genera el curation report en markdown."""

    # PII section
    pii_rows = []
    for pii_type, data in pii_findings.items():
        status = "✅ ENCONTRADO" if data["count"] > 0 else "❌ NO ENCONTRADO"
        pii_rows.append(f"| {data['description']} | {data['count']:,} | {status} |")

    pii_table = "\n".join(pii_rows)

    # Company section
    company_rows = []
    for company, data in company_findings.items():
        status = "✅ ENCONTRADO" if data["found"] else "❌ NO ENCONTRADO"
        columns = ", ".join(data["columns"]) if data["columns"] else "-"
        company_rows.append(f"| {company} | {status} | {columns} |")

    company_table = "\n".join(company_rows)

    report = f"""# Dataset Curation Report — CSIC 2010

**Fecha:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}
**Dataset:** `{input_path}`
**Total de filas:** {total_rows:,}

---

## Resumen

Este reporte documenta el análisis de PII (Personally Identifiable Information) y
referencias a empresas/organizaciones en el dataset CSIC 2010.

**Nota:** Este DAG solo escanea y reporta. No modifica el dataset.

---

## PII Encontrado

| Tipo de PII | Occurrencias | Estado |
|-------------|--------------|--------|
{pii_table}

### Detalle de hallazgos

"""

    for pii_type, data in pii_findings.items():
        if data["count"] > 0 and data["examples"]:
            report += f"\n#### {data['description']}\n"
            report += f"Ocurrencias: {data['count']:,}\n\n"
            report += "Ejemplos (primeros 3):\n"
            for i, ex in enumerate(data["examples"], 1):
                report += f"```\n{i}. {ex}\n```\n"

    report += f"""
---

## Empresas y Organizaciones Buscadas

| Empresa/Organización | Estado | Columnas |
|---------------------|--------|----------|
{company_table}

### Detalle de empresas

"""

    for company, data in company_findings.items():
        if data["found"]:
            report += f"\n#### {company}\n"
            report += f"✅ **ENCONTRADO**\n"
            report += f"Columnas: {', '.join(data['columns'])}\n"
            if data["sample"]:
                report += f"Muestra:\n```\n{data['sample']}\n```\n"
        else:
            report += f"\n#### {company}\n"
            report += "❌ **NO ENCONTRADO** — No hay referencias a esta empresa/organización en el dataset.\n"

    report += f"""
---

## Balance de Clases

| Clase | Cantidad | Porcentaje |
|-------|----------|------------|
| Normal | {class_balance['normal']:,} | {class_balance['normal_rate']:.1f}% |
| Ataque | {class_balance['attack']:,} | {class_balance['attack_rate']:.1f}% |
| **Total** | **{class_balance['total']:,}** | **100%** |

---

## Conclusiones

"""

    # Generate conclusions based on findings
    pii_found = [k for k, v in pii_findings.items() if v["count"] > 0]
    companies_found = [k for k, v in company_findings.items() if v["found"]]

    if pii_found or companies_found:
        report += "### ⚠️ Hallazgos importantes\n\n"
        if pii_found:
            report += f"Se encontró PII del siguiente tipo: {', '.join(pii_found)}.\n"
            report += "**Acción requerida:** Evaluar si estos datos deben ser removidos o anonimizados antes del training.\n\n"
        if companies_found:
            report += f"Se encontraron referencias a: {', '.join(companies_found)}.\n"
            report += "**Acción requerida:** Verificar que estos datos son legítimos para uso en training.\n\n"
    else:
        report += "### ✅ Sin problemas identificados\n\n"
        report += "No se encontró PII ni referencias a empresas externas en el dataset.\n"
        report += "El dataset está listo para ser usado en training sin modificaciones.\n\n"

    report += """---

## Sign-off

- [ ] MLOps (revisión de hallazgos completada)
- [ ] Decisión: ¿El dataset requiere sanitización adicional?

"""

    return report


def main():
    parser = argparse.ArgumentParser(description="Stage 0 — Curado del Dataset CSIC 2010")
    parser.add_argument("--input", required=True, help="Path al CSV de input")
    parser.add_argument("--report", required=True, help="Path al report markdown de output")
    args = parser.parse_args()

    input_path = Path(args.input)
    report_path = Path(args.report)

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        raise FileNotFoundError(input_path)

    print(f"Cargando dataset: {input_path}")
    df = pd.read_csv(input_path)
    total_rows = len(df)
    print(f"  Filas: {total_rows:,}")

    # 1. Scan PII
    print("\nEscaneando PII...")
    pii_findings = scan_pii(df)
    for pii_type, data in pii_findings.items():
        status = "ENCONTRADO" if data["count"] > 0 else "no encontrado"
        print(f"  {data['description']}: {data['count']:,} ({status})")

    # 2. Check companies
    print("\nBuscando empresas/organizaciones...")
    company_findings = check_company_references(df)
    for company, data in company_findings.items():
        status = "ENCONTRADO" if data["found"] else "no encontrado"
        print(f"  {company}: {status}")

    # 3. Analyze balance
    print("\nAnalizando balance de clases...")
    class_balance = analyze_class_balance(df)
    print(f"  Normal: {class_balance['normal']:,} ({class_balance['normal_rate']:.1f}%)")
    print(f"  Attack: {class_balance['attack']:,} ({class_balance['attack_rate']:.1f}%)")

    # Generate report
    print(f"\nGenerando report: {report_path}")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = generate_report(
        input_path=str(input_path),
        pii_findings=pii_findings,
        company_findings=company_findings,
        class_balance=class_balance,
        total_rows=total_rows,
    )
    report_path.write_text(report)

    print("\nEscaneo completado!")
    print(f"  Report: {report_path}")


if __name__ == "__main__":
    main()