# Forms only parse and check the input format. Business rules stay in the domain:
# its errors are shown on the form by the views.
from collections.abc import Iterable
from decimal import Decimal
from uuid import UUID

from django import forms

from rental.application.ports.inbound.create_rental import CreateRentalCommand
from rental.application.ports.inbound.list_available_equipment import ListAvailableEquipmentQuery
from rental.application.ports.inbound.register_customer import RegisterCustomerCommand
from rental.application.ports.inbound.register_equipment import RegisterEquipmentCommand
from rental.domain.equipment import EquipmentType, Range, size_unit_for
from rental.domain.size import Size
from rental.domain.skill_level import SkillLevel

TYPE_CHOICES = [(member.value, member.value.capitalize()) for member in EquipmentType]
RANGE_CHOICES = [(member.value, member.value.capitalize()) for member in Range]
LEVEL_CHOICES = [(member.value, member.value.capitalize()) for member in SkillLevel]


class RegisterEquipmentForm(forms.Form):
    type = forms.ChoiceField(choices=TYPE_CHOICES)
    brand = forms.CharField(max_length=100)
    model = forms.CharField(max_length=100)
    size = forms.DecimalField(
        max_digits=5,
        decimal_places=1,
        min_value=Decimal("0.1"),
        help_text="In cm, or in mondopoint for boots (e.g. 26.5).",
    )
    range = forms.ChoiceField(
        choices=[("", "No range (helmets, poles)"), *RANGE_CHOICES], required=False
    )

    def to_command(self) -> RegisterEquipmentCommand:
        data = self.cleaned_data
        equipment_type = EquipmentType(data["type"])
        return RegisterEquipmentCommand(
            type=equipment_type,
            brand=data["brand"],
            model=data["model"],
            size=Size(data["size"], size_unit_for(equipment_type)),
            range=Range(data["range"]) if data["range"] else None,
        )


class EquipmentFilterForm(forms.Form):
    type = forms.ChoiceField(choices=[("", "All types"), *TYPE_CHOICES], required=False)
    range = forms.ChoiceField(choices=[("", "All ranges"), *RANGE_CHOICES], required=False)

    def to_query(self) -> ListAvailableEquipmentQuery:
        data = self.cleaned_data if self.is_valid() else {}
        return ListAvailableEquipmentQuery(
            type=EquipmentType(data["type"]) if data.get("type") else None,
            range=Range(data["range"]) if data.get("range") else None,
        )


class RegisterCustomerForm(forms.Form):
    name = forms.CharField(max_length=200)
    height_cm = forms.IntegerField(label="Height (cm)", min_value=50, max_value=250)
    boot_size = forms.DecimalField(
        label="Boot size (mondopoint)",
        max_digits=4,
        decimal_places=1,
        min_value=Decimal("15"),
        max_value=Decimal("35"),
        help_text="Foot length in cm, e.g. 26.5.",
    )
    skill_level = forms.ChoiceField(choices=LEVEL_CHOICES)

    def to_command(self) -> RegisterCustomerCommand:
        data = self.cleaned_data
        return RegisterCustomerCommand(
            name=data["name"],
            height_cm=data["height_cm"],
            boot_size=Size.mondopoint(data["boot_size"]),
            skill_level=SkillLevel(data["skill_level"]),
        )


class CreateRentalForm(forms.Form):
    equipment = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        error_messages={"required": "Choose at least one item."},
    )
    end_date = forms.DateField(label="Last day", widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, item_ids: Iterable[UUID] = (), **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["equipment"].choices = [(str(item_id), str(item_id)) for item_id in item_ids]

    def to_command(self, customer_id: UUID) -> CreateRentalCommand:
        data = self.cleaned_data
        # The same item can be listed in two sections of the page: keep it once.
        equipment_ids = tuple(dict.fromkeys(UUID(value) for value in data["equipment"]))
        return CreateRentalCommand(
            customer_id=customer_id, equipment_ids=equipment_ids, end_date=data["end_date"]
        )


class ImportGroupForm(forms.Form):
    file = forms.FileField(label="CSV file")
    end_date = forms.DateField(label="Last day", widget=forms.DateInput(attrs={"type": "date"}))


def parse_ids(values: Iterable[str]) -> frozenset[UUID]:
    """Raises ValueError if a value is not a UUID."""
    return frozenset(UUID(value) for value in values)
