from src.data.applicant_repo import ApplicantRepo, STAGES
from src.data.models import Applicant, Property
from src.data.property_repo import PropertyRepo


def test_create_and_get(db):
    pid = PropertyRepo(db.conn).create(Property(address="1 Oak Ave"))
    repo = ApplicantRepo(db.conn)
    aid = repo.create(Applicant(applicant_name="John Doe", property_id=pid,
                                contact_info="555-1234"))
    got = repo.get(aid)
    assert got.applicant_name == "John Doe"
    assert got.screening_stage == "Inquiry Received"
    assert got.property_id == pid


def test_stage_validation(db):
    repo = ApplicantRepo(db.conn)
    aid = repo.create(Applicant(applicant_name="Jane"))
    for stage in STAGES:
        repo.set_stage(aid, stage)
        assert repo.get(aid).screening_stage == stage


def test_invalid_stage_rejected(db):
    repo = ApplicantRepo(db.conn)
    aid = repo.create(Applicant(applicant_name="Jane"))
    try:
        repo.set_stage(aid, "Bogus")
        failed = False
    except Exception:
        failed = True
    assert failed


def test_list_filters(db):
    pid = PropertyRepo(db.conn).create(Property(address="2 Elm St"))
    repo = ApplicantRepo(db.conn)
    a = repo.create(Applicant(applicant_name="A", property_id=pid))
    repo.create(Applicant(applicant_name="B", property_id=pid))
    repo.set_stage(a, "Approved")
    assert len(repo.list(property_id=pid, stage="Approved")) == 1
    assert len(repo.list(property_id=pid)) == 2


def test_documents(db):
    repo = ApplicantRepo(db.conn)
    aid = repo.create(Applicant(applicant_name="Doc"))
    repo.add_document(aid, "credit_report.pdf", "credit")
    docs = repo.documents(aid)
    assert len(docs) == 1 and docs[0]["kind"] == "credit"


def test_delete_cascades_documents(db):
    repo = ApplicantRepo(db.conn)
    aid = repo.create(Applicant(applicant_name="Gone"))
    repo.add_document(aid, "x.pdf")
    repo.delete(aid)
    assert repo.documents(aid) == []
