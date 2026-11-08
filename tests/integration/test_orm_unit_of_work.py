import pytest

from rental.adapters.outbound.orm.repositories import DjangoEquipmentRepository
from rental.adapters.outbound.orm.unit_of_work import DjangoUnitOfWork
from tests.unit.factories import make_skis

pytestmark = pytest.mark.django_db


def test_changes_are_kept_after_commit():
    repository, skis = DjangoEquipmentRepository(), make_skis()

    with DjangoUnitOfWork() as uow:
        repository.save(skis)
        uow.commit()

    assert repository.get(skis.id) == skis


def test_changes_are_rolled_back_without_commit():
    repository = DjangoEquipmentRepository()

    with DjangoUnitOfWork():
        repository.save(make_skis())

    assert repository.find_available() == []


def test_changes_are_rolled_back_on_error():
    repository = DjangoEquipmentRepository()

    with pytest.raises(RuntimeError), DjangoUnitOfWork() as uow:
        repository.save(make_skis())
        uow.commit()
        raise RuntimeError("something failed after the commit call")

    assert repository.find_available() == []
