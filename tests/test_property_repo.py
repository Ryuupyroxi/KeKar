from src.data.models import Property
from src.data.property_repo import PropertyRepo


def _sample(**kw):
    base = dict(address="123 Main St", city="Pawhuska", zip_code="74056",
                rent_price=850.0, deposit_amount=850.0, available_date="2026-12-01",
                bedrooms=3, bathrooms=2.0, sqft=1200, pet_policy="Cats OK",
                status="Vacant", amenity_wd=True, amenity_ac=True,
                amenity_yard=True, amenity_dishwasher=False, amenity_parking=True)
    base.update(kw)
    return Property(**base)


def test_create_and_get(db):
    repo = PropertyRepo(db.conn)
    pid = repo.create(_sample())
    assert pid > 0
    got = repo.get(pid)
    assert got.address == "123 Main St"
    assert got.rent_price == 850.0
    assert got.amenity_wd is True
    assert got.status == "Vacant"


def test_update(db):
    repo = PropertyRepo(db.conn)
    pid = repo.create(_sample())
    prop = repo.get(pid)
    prop.rent_price = 900.0
    prop.amenity_dishwasher = True
    repo.update(prop)
    assert repo.get(pid).rent_price == 900.0
    assert repo.get(pid).amenity_dishwasher is True


def test_set_status(db):
    repo = PropertyRepo(db.conn)
    pid = repo.create(_sample())
    repo.set_status(pid, "Rented")
    assert repo.get(pid).status == "Rented"


def test_list_filters_by_status(db):
    repo = PropertyRepo(db.conn)
    a = repo.create(_sample(address="A St"))
    b = repo.create(_sample(address="B St"))
    repo.set_status(b, "Rented")
    assert [p.id for p in repo.list(status="Vacant")] == [a]
    assert len(repo.list()) == 2


def test_delete(db):
    repo = PropertyRepo(db.conn)
    pid = repo.create(_sample())
    repo.delete(pid)
    assert repo.get(pid) is None
