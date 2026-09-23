from app.services.rail_engine import RailCandidate, Segment, choose_rail, first_fit, free_gaps


def test_first_fit_leftmost():
    occ = [Segment(20, 40)]
    p = first_fit(100, occ, 15)
    assert p is not None
    assert p.start_cm == 0
    assert p.end_cm == 15


def test_first_fit_skips_too_small_gap():
    occ = [Segment(0, 10), Segment(18, 50)]
    p = first_fit(100, occ, 10)
    assert p is not None
    assert p.start_cm == 50


def test_no_space():
    occ = [Segment(0, 80)]
    assert first_fit(100, occ, 25) is None


def test_free_gaps_edges():
    gaps = free_gaps(50, [Segment(10, 20), Segment(30, 35)])
    assert gaps == [Segment(0, 10), Segment(20, 30), Segment(35, 50)]


def test_blocked_rail_not_chosen_even_with_space():
    """封锁杆不被 First-Fit 选中：A 杆全空但检修中，必须落到 B 杆。"""
    candidates = [
        RailCandidate(rail_id=1, length_cm=200, occupied=[], blocked=True),
        RailCandidate(rail_id=2, length_cm=160, occupied=[Segment(0, 100)], blocked=False),
    ]
    chosen = choose_rail(candidates, 50)
    assert chosen is not None
    rail_id, place = chosen
    assert rail_id == 2
    assert (place.start_cm, place.end_cm) == (100, 150)


def test_all_rails_blocked_returns_none():
    candidates = [
        RailCandidate(rail_id=1, length_cm=200, occupied=[], blocked=True),
        RailCandidate(rail_id=2, length_cm=160, occupied=[], blocked=True),
    ]
    assert choose_rail(candidates, 40) is None


def test_blocked_rail_ordering_still_leftmost_after_unblock():
    candidates = [
        RailCandidate(rail_id=1, length_cm=200, occupied=[], blocked=False),
        RailCandidate(rail_id=2, length_cm=160, occupied=[], blocked=False),
    ]
    chosen = choose_rail(candidates, 40)
    assert chosen is not None
    assert chosen[0] == 1
