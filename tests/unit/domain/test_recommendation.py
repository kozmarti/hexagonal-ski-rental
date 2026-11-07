import pytest

from rental.domain.customer import Customer
from rental.domain.equipment import Equipment, EquipmentType, Range
from rental.domain.recommendation import Recommendation
from rental.domain.size import Size
from rental.domain.skill_level import SkillLevel


def customer(level: SkillLevel, height_cm: int = 175) -> Customer:
    return Customer.register("Alex Martin", height_cm, Size.mondopoint("26.5"), level)


@pytest.mark.parametrize(
    ("level", "range", "ski_cm", "snowboard_cm"),
    [
        (SkillLevel.BEGINNER, Range.DISCOVERY, 160, 150),
        (SkillLevel.INTERMEDIATE, Range.SPORT, 165, 155),
        (SkillLevel.ADVANCED, Range.PREMIUM, 170, 160),
        (SkillLevel.EXPERT, Range.PREMIUM, 175, 160),
    ],
)
def test_recommendation_depends_on_level_and_height(level, range, ski_cm, snowboard_cm):
    recommendation = Recommendation.for_customer(customer(level))

    assert recommendation.range is range
    assert recommendation.ski_length == Size.cm(ski_cm)
    assert recommendation.snowboard_length == Size.cm(snowboard_cm)
    assert recommendation.boot_size == Size.mondopoint("26.5")


@pytest.mark.parametrize(
    ("length", "fits"),
    [(160, True), (165, True), (170, True), (159, False), (171, False)],
)
def test_skis_fit_within_five_centimeters(length, fits):
    recommendation = Recommendation.for_customer(customer(SkillLevel.INTERMEDIATE))
    skis = Equipment.register(EquipmentType.SKIS, "Brand", "Model", Size.cm(length), Range.SPORT)

    assert recommendation.fits(skis) is fits


@pytest.mark.parametrize(
    ("size", "fits"),
    [("26", True), ("27", True), ("25.5", False), ("27.5", False)],
)
def test_boots_fit_within_half_a_size(size, fits):
    recommendation = Recommendation.for_customer(customer(SkillLevel.INTERMEDIATE))
    boots = Equipment.register(
        EquipmentType.BOOTS, "Brand", "Model", Size.mondopoint(size), Range.SPORT
    )

    assert recommendation.fits(boots) is fits


def test_items_from_another_range_do_not_fit():
    recommendation = Recommendation.for_customer(customer(SkillLevel.INTERMEDIATE))
    skis = Equipment.register(EquipmentType.SKIS, "Brand", "Model", Size.cm(165), Range.PREMIUM)

    assert not recommendation.fits(skis)


def test_helmets_are_never_recommended_by_size():
    recommendation = Recommendation.for_customer(customer(SkillLevel.INTERMEDIATE))
    helmet = Equipment.register(EquipmentType.HELMET, "Brand", "Model", Size.cm(58))

    assert not recommendation.fits(helmet)
