from datetime import datetime
from io import BytesIO
import unicodedata
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


EXPORT_HEADERS = ["Tipo", "Produto", "Quantidade", "Usuario", "Data", "Detalhe"]
PEDIDO_EXPORT_HEADERS = ["Produto", "Quantidade", "Solicitante", "Status", "Data", "Observacao"]


def build_movimentacoes_table(logs):
    return [EXPORT_HEADERS] + [_build_movimentacao_row(log_item) for log_item in logs]


def build_movimentacoes_xlsx(logs):
    table = build_movimentacoes_table(logs)
    return build_xlsx(table, "Movimentacoes")


def build_movimentacoes_pdf(logs):
    table = build_movimentacoes_table(logs)
    return build_pdf(table, "Registro de Entradas e Saidas")


def build_solicitacoes_table(pedidos):
    return [PEDIDO_EXPORT_HEADERS] + [_build_solicitacao_row(pedido) for pedido in pedidos]


def build_solicitacoes_xlsx(pedidos):
    table = build_solicitacoes_table(pedidos)
    return build_xlsx(table, "Solicitacoes")


def build_solicitacoes_pdf(pedidos):
    table = build_solicitacoes_table(pedidos)
    return build_pdf(table, "Registro de Solicitacoes")


def export_filename(extension, prefix="registro-movimentacoes"):
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    return f"{prefix}-{timestamp}.{extension}"


def _build_movimentacao_row(log_item):
    return [
        log_item.get("tipo_label", ""),
        log_item.get("epi_nome", ""),
        _format_quantity(log_item),
        log_item.get("usuario_nome", ""),
        _format_date(log_item.get("data")),
        _detail_label(log_item.get("tipo")),
    ]


def _build_solicitacao_row(pedido):
    return [
        pedido.get("epi_nome", ""),
        f"{pedido.get('quantidade', '')} unidade(s)",
        pedido.get("usuario_nome", ""),
        pedido.get("status_label", pedido.get("status", "")),
        _format_date(pedido.get("data_pedido")),
        pedido.get("observacao") or "Sem observacao.",
    ]


def _format_quantity(log_item):
    quantity = log_item.get("quantidade", "")
    if log_item.get("tipo") == 2:
        try:
            numeric_quantity = int(quantity)
        except (TypeError, ValueError):
            return str(quantity)
        if numeric_quantity > 0:
            return f"+{numeric_quantity}"
    return str(quantity)


def _format_date(value):
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y %H:%M")
    return str(value or "")


def _detail_label(log_type):
    if log_type == 1:
        return "Entrada registrada"
    if log_type == 2:
        return "Edicao de estoque"
    if log_type == 3:
        return "Saida registrada"
    return "Movimentacao"


def build_xlsx(table, sheet_name):
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as workbook:
        workbook.writestr("[Content_Types].xml", _xlsx_content_types())
        workbook.writestr("_rels/.rels", _xlsx_root_rels())
        workbook.writestr("docProps/app.xml", _xlsx_app_props())
        workbook.writestr("docProps/core.xml", _xlsx_core_props())
        workbook.writestr("xl/workbook.xml", _xlsx_workbook(sheet_name))
        workbook.writestr("xl/_rels/workbook.xml.rels", _xlsx_workbook_rels())
        workbook.writestr("xl/styles.xml", _xlsx_styles())
        workbook.writestr("xl/worksheets/sheet1.xml", _xlsx_sheet(table))
    return buffer.getvalue()


def _xlsx_content_types():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""


def _xlsx_root_rels():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""


def _xlsx_workbook(sheet_name):
    safe_sheet_name = escape(sheet_name[:31])
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="{safe_sheet_name}" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>"""


def _xlsx_workbook_rels():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""


def _xlsx_styles():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><name val="Calibri"/></font>
  </fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border/></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="2">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0"/>
  </cellXfs>
</styleSheet>"""


def _xlsx_app_props():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Gerenciador</Application>
</Properties>"""


def _xlsx_core_props():
    created_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Registro de movimentacoes</dc:title>
  <dc:creator>Gerenciador</dc:creator>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created_at}</dcterms:created>
</cp:coreProperties>"""


def _xlsx_sheet(table):
    rows_xml = []
    for row_number, row in enumerate(table, start=1):
        cells_xml = []
        for column_number, value in enumerate(row, start=1):
            cell_reference = f"{_column_letter(column_number)}{row_number}"
            style = ' s="1"' if row_number == 1 else ""
            cell_value = _xlsx_text(value)
            cells_xml.append(
                f'<c r="{cell_reference}" t="inlineStr"{style}><is><t>{cell_value}</t></is></c>'
            )
        rows_xml.append(f'<row r="{row_number}">{"".join(cells_xml)}</row>')

    dimension = f"A1:{_column_letter(len(table[0]))}{max(len(table), 1)}"
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="{dimension}"/>
  <cols>
    <col min="1" max="1" width="24" customWidth="1"/>
    <col min="2" max="2" width="32" customWidth="1"/>
    <col min="3" max="3" width="14" customWidth="1"/>
    <col min="4" max="4" width="26" customWidth="1"/>
    <col min="5" max="5" width="20" customWidth="1"/>
    <col min="6" max="6" width="24" customWidth="1"/>
  </cols>
  <sheetData>
    {"".join(rows_xml)}
  </sheetData>
</worksheet>"""


def _xlsx_text(value):
    return escape(str(value), {'"': "&quot;"})


def _column_letter(column_number):
    letters = ""
    while column_number:
        column_number, remainder = divmod(column_number - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def build_pdf(table, title):
    page_width = 842
    page_height = 595
    margin_x = 34
    start_y = 540
    row_height = 16
    rows_per_page = 29
    column_positions = [34, 190, 388, 456, 590, 704]
    column_widths = [150, 190, 60, 128, 108, 104]

    body_rows = table[1:] or [["Sem registros", "", "", "", "", ""]]
    pages = []
    for page_index, chunk_start in enumerate(range(0, len(body_rows), rows_per_page), start=1):
        chunk = body_rows[chunk_start:chunk_start + rows_per_page]
        lines = [
            _pdf_text_line(margin_x, 565, title, size=15, font="F2"),
            _pdf_text_line(margin_x, 548, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", size=9),
        ]
        y = start_y - 22
        for col_index, header in enumerate(table[0]):
            lines.append(_pdf_text_line(column_positions[col_index], y, header, size=8, font="F2"))
        y -= row_height
        lines.append(_pdf_line(margin_x, y + 8, page_width - margin_x, y + 8))
        for row in chunk:
            for col_index, value in enumerate(row):
                lines.append(
                    _pdf_text_line(
                        column_positions[col_index],
                        y,
                        _clip_text(value, column_widths[col_index]),
                        size=8,
                    )
                )
            y -= row_height
        lines.append(_pdf_text_line(page_width - 80, 24, f"Pagina {page_index}", size=8))
        pages.append("\n".join(lines))

    return _assemble_pdf(pages, page_width, page_height)


def _clip_text(value, max_width):
    text = _ascii_text(value)
    max_chars = max_width // 5
    if len(text) <= max_chars:
        return text
    return text[: max(max_chars - 3, 1)] + "..."


def _ascii_text(value):
    text = str(value)
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def _pdf_text_line(x, y, text, size=10, font="F1"):
    safe_text = _pdf_escape(_ascii_text(text))
    return f"BT /{font} {size} Tf {x} {y} Td ({safe_text}) Tj ET"


def _pdf_line(x1, y1, x2, y2):
    return f"{x1} {y1} m {x2} {y2} l S"


def _pdf_escape(value):
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _assemble_pdf(page_streams, page_width, page_height):
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        None,
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
    ]
    page_refs = []
    for stream in page_streams:
        stream_bytes = stream.encode("latin-1")
        page_object_number = len(objects) + 1
        content_object_number = len(objects) + 2
        page_refs.append(f"{page_object_number} 0 R")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
            f"/Contents {content_object_number} 0 R >>"
        )
        objects.append(
            f"<< /Length {len(stream_bytes)} >>\nstream\n{stream}\nendstream"
        )

    objects[1] = f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(page_refs)} >>"

    output = BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]
    for object_number, object_body in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{object_number} 0 obj\n{object_body}\nendobj\n".encode("latin-1"))

    xref_offset = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("latin-1"))
    output.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode("latin-1")
    )
    return output.getvalue()
