from src.data.chat_repo import ChatRepo


def test_history_order_and_limit(db):
    repo = ChatRepo(db.conn)
    for i in range(5):
        repo.add("user", f"m{i}")
    assert [m["content"] for m in repo.history(limit=3)] == ["m2", "m3", "m4"]


def test_clear(db):
    repo = ChatRepo(db.conn)
    repo.add("user", "hi")
    repo.clear()
    assert repo.history() == []
