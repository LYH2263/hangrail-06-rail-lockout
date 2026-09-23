from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.models import HangRail, RailPlacement, Store, WorkOrder
from app.services.seed import seed_if_empty


def make_store_with_rails(maintenance_a=0, maintenance_b=0):
    db = SessionLocal()
    try:
        store = Store(name="测试店")
        db.add(store)
        db.flush()
        a = HangRail(store_id=store.id, label="A 杆", length_cm=200, maintenance=maintenance_a)
        b = HangRail(store_id=store.id, label="B 杆", length_cm=160, maintenance=maintenance_b)
        db.add_all([a, b])
        db.commit()
        return store.id, a.id, b.id
    finally:
        db.close()


def make_order(store_id, ticket="T-1", length_cm=50, status="ready"):
    db = SessionLocal()
    try:
        order = WorkOrder(
            store_id=store_id,
            ticket_code=ticket,
            garment_name="测试衣物",
            length_cm=length_cm,
            status=status,
            due_at=datetime.utcnow() + timedelta(days=1),
        )
        db.add(order)
        db.commit()
        return order.id
    finally:
        db.close()


def lock(client, rail_id, locked=True):
    resp = client.post(f"/api/rails/{rail_id}/maintenance", json={"maintenance": locked})
    assert resp.status_code == 200
    return resp


def hung_rail_id(order_id):
    db = SessionLocal()
    try:
        p = db.query(RailPlacement).filter_by(order_id=order_id, active=1).one()
        return p.rail_id
    finally:
        db.close()


def test_locked_rail_not_selected_by_first_fit(client):
    """封锁杆不被 First-Fit 选中：A 杆封锁后 ready 工单只能上 B 杆。"""
    store_id, a_id, b_id = make_store_with_rails(maintenance_a=1)
    order_id = make_order(store_id, length_cm=50)

    resp = client.post("/api/hang", json={"order_id": order_id})

    assert resp.status_code == 200
    assert resp.json()["status"] == "hung"
    assert hung_rail_id(order_id) == b_id
    assert client.get(f"/api/occupancy/{a_id}").json()["segments"] == []


def test_locked_rail_skipped_even_when_explicitly_requested(client):
    store_id, a_id, _ = make_store_with_rails(maintenance_a=1)
    order_id = make_order(store_id)

    resp = client.post("/api/hang", json={"order_id": order_id, "rail_id": a_id})

    assert resp.status_code == 409
    assert "检修" in resp.json()["detail"]


def test_all_rails_locked_error_mentions_maintenance(client):
    """全杆封锁时上杆失败，提示含检修语义。"""
    store_id, _, _ = make_store_with_rails(maintenance_a=1, maintenance_b=1)
    order_id = make_order(store_id)

    resp = client.post("/api/hang", json={"order_id": order_id})

    assert resp.status_code == 409
    assert "检修" in resp.json()["detail"]


def test_pickup_still_works_on_locked_rail(client):
    """封锁杆上仍可取件：取件释放占位。"""
    store_id, a_id, _ = make_store_with_rails()
    order_id = make_order(store_id, ticket="T-LOCK", length_cm=50)
    assert client.post("/api/hang", json={"order_id": order_id, "rail_id": a_id}).status_code == 200
    assert hung_rail_id(order_id) == a_id

    lock(client, a_id, True)
    resp = client.post("/api/pickup", json={"ticket_code": "T-LOCK"})

    assert resp.status_code == 200
    assert resp.json()["status"] == "picked"
    assert client.get(f"/api/occupancy/{a_id}").json()["segments"] == []


def test_unlock_restores_hanging(client):
    """解除封锁后恢复可挂。"""
    store_id, a_id, _ = make_store_with_rails(maintenance_a=1)
    order_id = make_order(store_id, length_cm=50)
    assert client.post("/api/hang", json={"order_id": order_id}).status_code == 200
    assert hung_rail_id(order_id) != a_id

    lock(client, a_id, False)
    order2 = make_order(store_id, ticket="T-2", length_cm=50)
    resp = client.post("/api/hang", json={"order_id": order2})

    assert resp.status_code == 200
    assert hung_rail_id(order2) == a_id


def test_maintenance_state_persisted_in_rail_list(client):
    """切换封锁后再次拉取挂杆列表仍保持。"""
    _, a_id, b_id = make_store_with_rails()
    lock(client, a_id, True)

    rails = {r["id"]: r for r in client.get("/api/rails").json()}
    assert rails[a_id]["maintenance"] is True
    assert rails[b_id]["maintenance"] is False


def test_seed_locks_rail_a_so_ready_orders_use_rail_b(client):
    """种子：封锁 A 杆后 ready 工单只能尝试 B 杆。"""
    db = SessionLocal()
    try:
        seed_if_empty(db)
        a = db.query(HangRail).filter_by(label="A 杆").one()
        b = db.query(HangRail).filter_by(label="B 杆").one()
        assert a.maintenance == 1
        assert b.maintenance == 0
        ready = db.query(WorkOrder).filter_by(ticket_code="HR-2003").one()
        ready_id = ready.id
        b_id = b.id
    finally:
        db.close()

    resp = client.post("/api/hang", json={"order_id": ready_id})

    assert resp.status_code == 200
    assert hung_rail_id(ready_id) == b_id
