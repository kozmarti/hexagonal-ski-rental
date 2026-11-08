# Django ORM models: persistence details only, mapped to domain entities by the repositories.
from django.db import models

from rental.domain.equipment import EquipmentStatus, EquipmentType, Range
from rental.domain.rental import RentalStatus
from rental.domain.size import SizeUnit
from rental.domain.skill_level import SkillLevel


def choices(enum):
    return [(member.value, member.value) for member in enum]


class EquipmentModel(models.Model):
    id = models.UUIDField(primary_key=True)
    type = models.CharField(max_length=20, choices=choices(EquipmentType))
    brand = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    size_value = models.DecimalField(max_digits=5, decimal_places=1)
    size_unit = models.CharField(max_length=20, choices=choices(SizeUnit))
    range = models.CharField(max_length=20, choices=choices(Range), null=True, blank=True)
    status = models.CharField(max_length=20, choices=choices(EquipmentStatus))
    days_used = models.PositiveIntegerField(default=0)
    needs_repair = models.BooleanField(default=False)

    class Meta:
        db_table = "equipment"


class CustomerModel(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=200)
    height_cm = models.PositiveSmallIntegerField()
    boot_size_value = models.DecimalField(max_digits=5, decimal_places=1)
    boot_size_unit = models.CharField(max_length=20, choices=choices(SizeUnit))
    skill_level = models.CharField(max_length=20, choices=choices(SkillLevel))

    class Meta:
        db_table = "customer"


class RentalModel(models.Model):
    id = models.UUIDField(primary_key=True)
    customer = models.ForeignKey(CustomerModel, on_delete=models.PROTECT, related_name="rentals")
    start_date = models.DateField()
    end_date = models.DateField()
    price_amount = models.DecimalField(max_digits=8, decimal_places=2)
    price_currency = models.CharField(max_length=3)
    status = models.CharField(max_length=20, choices=choices(RentalStatus))
    returned_on = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "rental"


class RentalItemModel(models.Model):
    """The items of a rental. Saved with the rental by RentalRepository, not on their own."""

    rental = models.ForeignKey(RentalModel, on_delete=models.CASCADE, related_name="items")
    equipment = models.ForeignKey(
        EquipmentModel, on_delete=models.PROTECT, related_name="rental_items"
    )
    position = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "rental_item"
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["rental", "equipment"], name="unique_rental_item"),
        ]
