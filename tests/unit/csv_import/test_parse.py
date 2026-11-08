from decimal import Decimal

import pytest

from rental.adapters.inbound.csv_import.importer import CsvFormatError, parse
from rental.domain.equipment import EquipmentType
from rental.domain.skill_level import SkillLevel

HEADER = "name,height_cm,boot_size,level,board,helmet"


def test_reads_one_member_per_line():
    members = parse(f"{HEADER}\nEmma Laurent,170,25.5,beginner,skis,yes\n")

    assert len(members) == 1
    emma = members[0]
    assert (emma.line, emma.name, emma.height_cm) == (2, "Emma Laurent", 170)
    assert emma.boot_size == Decimal("25.5")
    assert emma.level is SkillLevel.BEGINNER
    assert emma.board is EquipmentType.SKIS
    assert emma.helmet is True


def test_accepts_semicolons_and_decimal_commas_from_a_french_spreadsheet():
    text = "\n".join(
        [
            "name;height_cm;boot_size;level;board;helmet",
            "Chloé Garnier;175;26,5;Beginner;Snowboard;no",
        ]
    )

    chloe = parse(text)[0]

    assert chloe.boot_size == Decimal("26.5")
    assert chloe.board is EquipmentType.SNOWBOARD
    assert chloe.helmet is False


def test_missing_column_is_reported():
    with pytest.raises(CsvFormatError, match="missing column"):
        parse("name,height_cm,boot_size,level,board\nEmma,170,25.5,beginner,skis\n")


def test_every_wrong_line_is_reported_with_its_number():
    text = "\n".join(
        [
            HEADER,
            "Emma,170,25.5,beginner,skis,yes",
            "Lucas,tall,27,beginner,skis,yes",
            ",170,25,expert,ski,maybe",
        ]
    )

    with pytest.raises(CsvFormatError) as error:
        parse(text)

    assert error.value.problems == [
        "Line 3: height_cm and boot_size must be numbers.",
        "Line 4: name is empty.",
    ]


def test_unknown_values_are_explained():
    with pytest.raises(CsvFormatError, match="Line 2: board must be skis or snowboard."):
        parse(f"{HEADER}\nEmma,170,25.5,beginner,sledge,yes\n")


def test_a_file_without_children_is_refused():
    with pytest.raises(CsvFormatError, match="no children"):
        parse(f"{HEADER}\n")
