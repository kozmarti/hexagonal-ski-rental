# Forms only parse and check the input format. Business rules stay in the domain:
# its errors are shown on the form by the views.
from decimal import Decimal

from django import forms

from rental.application.ports.inbound.list_available_equipment import ListAvailableEquipmentQuery
from rental.application.ports.inbound.register_equipment import RegisterEquipmentCommand
from rental.domain.equipment import EquipmentType, Range, size_unit_for
from rental.domain.size import Size

TYPE_CHOICES = [(member.value, member.value.capitalize()) for member in EquipmentType]
RANGE_CHOICES = [(member.value, member.value.capitalize()) for member in Range]


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
