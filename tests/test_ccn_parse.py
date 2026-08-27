"""Tests for the CCN vocabulary parser (Step 1: parse only, no rules).

Fixtures are built in-memory with openpyxl so the real workbook is never
committed. The synthetic sheets mimic the real hazards:
  * sheet ``17-*`` = eight independent vertical vocab lists parked side by
    side with blank spacer columns (row 2 = SECTION HEADER, row 3 = column
    sub-header, row 4 = blank spacer, row 5+ = data).
  * sheet ``05-Views`` = a real data table plus loose guidance prose and a
    stale ``(X)``-coded superseded block that must be skipped-and-counted.
"""
import openpyxl
import pytest

from agent.ccn import parse as ccn_parse


# --- eight sheet-17 blocks: (header_col, code_col_or_None, header, subheader, data rows) ---
_BLOCKS = [
    ("B", "C", "REVIT CATEGORIES", ("Revit Category Name", "Abbreviation"),
     [("AIRT_Air Terminals", "AIRT"), ("DOOR_Doors", "DOOR")]),
    ("E", "F", "UNIFORMAT CLASSIFICATIONS & CODES", ("Number  & Section Name", "Uniformat #"),
     [("1010      Project Summary", "1010"), ("Z9090      Financing Costs", "Z9090")]),
    ("H", None, "LEVELS", ("Levels", None),
     [("-02", None), ("-01", None), ("L1", None)]),
    ("J", "K", "CONSTRUCTION NATURE", ("Nature", "Nature-2"),
     [("NEW_New", "NEW"), ("EXD_Existing-Demolition", "EXD")]),
    ("M", "N", "DISCIPLINES", ("Discipline", "Disc-2"),
     [("ar-Architecture", "ar"), ("fa_Facility Analysis", "fa")]),
    ("P", None, "FAMILIES", ("Adjectives-Families", None),
     [("4-Drwr", None), ("Data", None)]),
    ("R", "S", "ORGANIZATIONS", ("Organization Name", "Organization Code"),
     [("Syntec Group", "syn"), ("IMEG", "imeg")]),
    ("U", None, "SHEETS", ("Sheet #_Name", None),
     [("G,000_General", None), ("A,100_Plans", None)]),
]


def _build_workbook(path):
    wb = openpyxl.Workbook()
    ws17 = wb.active
    ws17.title = "17-Fixture CNN Data"  # resolved by the "17-" prefix, not full name
    for header_col, code_col, header, (sub_a, sub_b), rows in _BLOCKS:
        ws17[f"{header_col}2"] = header
        ws17[f"{header_col}3"] = sub_a
        if code_col and sub_b:
            ws17[f"{code_col}3"] = sub_b
        r = 5  # row 4 stays blank (spacer)
        for value, code in rows:
            ws17[f"{header_col}{r}"] = value
            if code_col and code is not None:
                ws17[f"{code_col}{r}"] = code
            r += 1
    # A prose cell far outside the eight blocks — not scanned, not a block.
    ws17["AZ40"] = "guidance prose living nowhere near the vocab blocks"

    wsv = wb.create_sheet("05-Views")
    wsv["A1"] = "View Type"
    wsv["B1"] = "Abbreviation_View Type"
    wsv["C1"] = "Level"
    wsv["A2"] = "Floor Plan"
    wsv["B2"] = "FP_Floor Plan"
    wsv["C2"] = "L1"
    wsv["B3"] = "CP_Ceiling Plan"
    # guidance prose sitting in a data-looking area (length > 60 -> prose)
    wsv["E5"] = ("These views and sheets are not used anymore; see the note. "
                 "Use consistent abbreviations everywhere.")
    # stale superseded block: a column of "(X)"-coded values
    wsv["G2"] = "Civil (C)"
    wsv["G3"] = "Demo (D)"

    wb.save(path)


@pytest.fixture
def workbook(tmp_path):
    p = tmp_path / "ccn_fixture.xlsx"
    _build_workbook(str(p))
    return str(p)


def test_finds_all_eight_sheet17_vocabularies(workbook):
    result = ccn_parse.parse_workbook(workbook)
    names = [v.name for v in result.vocabularies if v.sheet.startswith("17-")]
    assert names == [
        "Revit Categories", "Uniformat", "Levels", "Construction Nature",
        "Disciplines", "Families", "Organizations", "Sheet Classifications",
    ]


def test_vocab_entries_are_plausible(workbook):
    result = ccn_parse.parse_workbook(workbook)
    by_name = {v.name: v for v in result.vocabularies}

    levels = by_name["Levels"]
    assert levels.count == 3
    assert levels.first == "-02"
    assert levels.last == "L1"

    revit = by_name["Revit Categories"]
    assert revit.count == 2
    assert revit.first == "AIRT_Air Terminals"
    assert revit.entries[0].code == "AIRT"  # adjacent code column captured

    uniformat = by_name["Uniformat"]
    assert uniformat.count == 2
    assert uniformat.last == "Z9090      Financing Costs"


def test_non_data_cells_are_counted_not_dropped(workbook):
    result = ccn_parse.parse_workbook(workbook)
    # sheet-17 section-header + sub-header cells inside the eight blocks (21)
    # + Views prose (1) + Views stale (2) = 24
    assert result.ignored_cells == 24
    assert result.ignored_breakdown["17"] == 21
    assert result.ignored_breakdown["05-Views"] == 3


def test_views_prose_and_stale_not_mistaken_for_data(workbook):
    result = ccn_parse.parse_workbook(workbook)
    # the guidance prose and the stale "(X)" block must never surface as vocab entries
    all_values = [e.value for v in result.vocabularies for e in v.entries]
    assert not any("not used anymore" in val for val in all_values)
    assert not any(val.endswith("(C)") or val.endswith("(D)") for val in all_values)


def test_report_lists_every_vocab_and_ignored_line(workbook):
    result = ccn_parse.parse_workbook(workbook)
    report = ccn_parse.format_report(result)
    assert "Revit Categories" in report
    assert "Sheet Classifications" in report
    assert "cells ignored as non-data" in report
    assert "24" in report
