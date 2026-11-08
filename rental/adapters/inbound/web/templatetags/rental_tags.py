from django import template

from rental.domain.money import Money
from rental.domain.size import Size

register = template.Library()


@register.filter
def size(value: Size) -> str:
    """160 cm, 26.5 mondopoint."""
    return f"{value.value.normalize():f} {value.unit}"


@register.filter
def money(value: Money) -> str:
    """180.00 EUR."""
    return f"{value.amount} {value.currency}"


@register.filter
def needing_repair(items):
    """The items flagged for repair, from a list of EquipmentView."""
    return [item for item in items if item.needs_repair]
