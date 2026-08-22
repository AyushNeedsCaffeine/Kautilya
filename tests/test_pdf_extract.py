from __future__ import annotations

from kautilya.ingestion.pdf_extract import split_constitution, split_numbered_provisions


CONSTITUTION_SAMPLE = """PREAMBLE
WE, THE PEOPLE OF INDIA
PART III
FUNDAMENTAL RIGHTS
12. Definition.—In this Part, unless the context otherwise requires,
"the State" includes the Government and Parliament of India.
13. Laws inconsistent with or in derogation of the fundamental rights.—(1) All laws in force
in the territory of India shall be void.
detention. 45. The State shall endeavour to provide, within a period of ten years from the
commencement of this Constitution, for free and compulsory education.
2[226. (1) Notwithstanding anything in article 32 every High Court shall have power,
throughout the territories in relation to which it exercises jurisdiction.
14.
Salaries, etc., of Judges.

(2) When a Judge has been transferred.
APPENDIX I"""


def test_split_constitution_handles_all_layout_variants() -> None:
    provisions = {num: (title, body) for num, title, body in split_constitution(CONSTITUTION_SAMPLE)}

    assert set(provisions) == {"12", "13", "45", "226"}

    title_13, body_13 = provisions["13"]
    assert title_13 == "Laws inconsistent with or in derogation of the fundamental rights"
    assert body_13.startswith("13.")

    title_45, _ = provisions["45"]
    assert title_45.startswith("The State shall endeavour")

    title_226, body_226 = provisions["226"]
    assert body_226.startswith("226.")
    assert "Notwithstanding anything in article 32" in body_226

    _, body_12 = provisions["12"]
    assert '"the State" includes' in body_12


CRPC_SAMPLE = """THE CODE OF CRIMINAL PROCEDURE, 1973
CHAPTER I
PRELIMINARY
1. Short title, extent and commencement.—(1) This Act may be called the Code of Criminal Procedure, 1973.
41A. Notice of appearance before police officer.—The police officer may issue a notice.
2. Definitions.
First Schedule"""


def test_split_numbered_provisions_dedup_keeps_longest() -> None:
    provisions = split_numbered_provisions(CRPC_SAMPLE)

    nums = [num for num, _, _ in provisions]
    assert nums == ["1", "41A", "2"]

    by_num = {num: body for num, _, body in provisions}
    assert by_num["1"].startswith("(1) This Act may be called")
    assert "may issue a notice" in by_num["41A"]
