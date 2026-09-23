from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.models import HangRail, RailPlacement, Store, WorkOrder


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), TestingSessionLocal
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _world(SessionLocal, a_blocked=True):
    """A 杆（默认检修封锁）上有一件已挂衣物；另有两件 ready 工单。"""
    db = SessionLocal()
    store = Store(name="测试门店")
    db.add(store)
    db.flush()
    ra = HangRail(store_id=store.id, label="A 杆", length_cm=200, blocked=1 if a_blocked else 0)
    rb = HangRail(store_id=store.id, label="B 杆", length_cm=160, blocked=0)
    db.add_all([ra, rb])
    db.flush()
    now = datetime.utcnow()
    hung = WorkOrder(
        store_id=store.id, ticket_code="HR-T1", garment_name="大衣", length_cm=45,
        status="hung", due_at=now + timedelta(days=1), hung_at=now,
    )
    ready1 = WorkOrder(
        store_id=store.id, ticket_code="HR-T2", garment_name="羽绒服", length_cm=50,
        status="ready", due_at=now + timedelta(days=1),
    )
    ready2 = WorkOrder(
        store_id=store.id, ticket_code="HR-T3", garment_name="风衣", length_cm=40,
        status="ready", due_at=now + timedelta(days=1),
    )
    db.add_all([hung, ready1, ready2])
    db.flush()
    db.add(RailPlacement(rail_id=ra.id, order_id=hung.id, start_cm=0, end_cm=45))
    db.commit()
    ids = dict(store=store.id, a=ra.id, b=rb.id, hung=hung.id, ready1=ready1.id, ready2=ready2.id)
    db.close()
    return ids


def _segments(c, rail_id):
    return c.get(f"/api/occupancy/{rail_id}").json()["segments"]


def test_ready_order_skips_blocked_rail_and_hangs_on_b(client):
    """封锁 A 杆后，ready 工单只能尝试 B 杆。"""
    c, SessionLocal = client
    ids = _world(SessionLocal)

    res = c.post("/api/hang", json={"order_id": ids["ready1"]})
    assert res.status_code == 200
    assert res.json()["status"] == "hung"

    assert [s["ticket_code"] for s in _segments(c, ids["a"])] == ["HR-T1"]  # A 杆维持原状，无新占位
    b_segs = _segments(c, ids["b"])
    assert [s["ticket_code"] for s in b_segs] == ["HR-T2"]
    assert b_segs[0]["start_cm"] == 0  # B 杆从空杆起挂


def test_all_rails_blocked_failure_has_maintenance_semantics(client):
    """全杆封锁时上杆失败，提示含检修语义。"""
    c, SessionLocal = client
    ids = _world(SessionLocal)
    r = c.patch(f"/api/rails/{ids['b']}/block", json={"blocked": True})
    assert r.status_code == 200 and r.json()["blocked"] is True

    res = c.post("/api/hang", json={"order_id": ids["ready1"]})
    assert res.status_code == 409
    detail = res.json()["detail"]
    assert "检修" in detail and "封锁" in detail


def test_explicit_hang_onto_blocked_rail_rejected(client):
    """指定封锁杆上杆同样被拒，提示含检修语义。"""
    c, SessionLocal = client
    ids = _world(SessionLocal)

    res = c.post("/api/hang", json={"order_id": ids["ready1"], "rail_id": ids["a"]})
    assert res.status_code == 409
    assert "检修" in res.json()["detail"]
    # 工单仍为 ready，A 杆未新增占位（HR-T1 原样保留），B 杆为空
    assert c.get("/api/orders").json()  # smoke
    assert [s["ticket_code"] for s in _segments(c, ids["a"])] == ["HR-T1"]
    assert _segments(c, ids["b"]) == []


def test_pickup_still_works_on_blocked_rail(client):
    """封锁杆上已有衣物仍允许取件释放占位。"""
    c, SessionLocal = client
    ids = _world(SessionLocal)
    assert [s["ticket_code"] for s in _segments(c, ids["a"])] == ["HR-T1"]

    res = c.post("/api/pickup", json={"ticket_code": "HR-T1"})
    assert res.status_code == 200
    assert res.json()["status"] == "picked"
    assert _segments(c, ids["a"]) == []


def test_unblock_restores_hanging(client):
    """解除封锁后恢复可挂，且 First-Fit 重新选中 A 杆。"""
    c, SessionLocal = client
    ids = _world(SessionLocal)

    r = c.patch(f"/api/rails/{ids['a']}/block", json={"blocked": False})
    assert r.status_code == 200 and r.json()["blocked"] is False

    res = c.post("/api/hang", json={"order_id": ids["ready1"]})
    assert res.status_code == 200
    # A 杆恢复可挂；HR-T2 紧接 HR-T1（0-45）之后 First-Fit
    a_segs = _segments(c, ids["a"])
    assert [s["ticket_code"] for s in a_segs] == ["HR-T1", "HR-T2"]
    assert (a_segs[1]["start_cm"], a_segs[1]["end_cm"]) == (45, 95)


def test_block_toggle_persists_across_refetch(client):
    """切换封锁后再次进入（重新拉取）状态保持。"""
    c, SessionLocal = client
    ids = _world(SessionLocal)

    assert c.patch(f"/api/rails/{ids['b']}/block", json={"blocked": True}).json()["blocked"] is True
    # 重新请求 /rails，相当于再次进入挂杆页
    rails = {r["id"]: r["blocked"] for r in c.get("/api/rails").json()}
    assert rails[ids["a"]] is True
    assert rails[ids["b"]] is True

    assert c.patch(f"/api/rails/{ids['a']}/block", json={"blocked": False}).json()["blocked"] is False
    rails = {r["id"]: r["blocked"] for r in c.get("/api/rails").json()}
    assert rails[ids["a"]] is False
    assert rails[ids["b"]] is True
