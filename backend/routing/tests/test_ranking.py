from routing.services.risk import RouteScore, rank_routes


def miles(no_travel=0, severe=0, high=0):
    return {
        "low": 0,
        "moderate": 0,
        "high": high,
        "severe": severe,
        "no_travel": no_travel,
        "no_data": 0,
    }


def ids(ranked):
    return [r.id for r in ranked]


def test_no_travel_routes_rank_last():
    ranked = rank_routes(
        [
            RouteScore(0, miles(no_travel=5), 0.5, 3600),
            RouteScore(1, miles(severe=50), 2.0, 7200),
        ]
    )
    assert ids(ranked) == [1, 0]
    assert ranked[0].reason == "Fewest No Travel miles"
    assert ranked[1].reason == "More No Travel miles"


def test_fewer_no_travel_miles_wins_among_no_travel_routes():
    ranked = rank_routes(
        [RouteScore(0, miles(no_travel=20), 1, 1), RouteScore(1, miles(no_travel=5), 1, 1)]
    )
    assert ids(ranked) == [1, 0]


def test_severe_then_high_miles():
    ranked = rank_routes(
        [
            RouteScore(0, miles(severe=10), 1.0, 3600),
            RouteScore(1, miles(high=100), 1.5, 3600),
            RouteScore(2, miles(high=50), 1.5, 3600),
        ]
    )
    assert ids(ranked) == [2, 1, 0]
    assert [r.rank for r in ranked] == [1, 2, 3]
    assert ranked[0].reason == "Fewest High miles"
    assert ranked[2].reason == "More Severe miles"


def test_avg_risk_then_duration():
    ranked = rank_routes(
        [
            RouteScore(0, miles(), 1.0, 3600),
            RouteScore(1, miles(), 0.5, 7200),
            RouteScore(2, miles(), 0.5, 5400),
        ]
    )
    assert ids(ranked) == [2, 1, 0]
    assert ranked[0].reason == "Shortest travel time"
    assert ranked[2].reason == "Higher average risk"


def test_ties_keep_router_order():
    ranked = rank_routes([RouteScore(0, miles(), 1.0, 3600), RouteScore(1, miles(), 1.0, 3600)])
    assert ids(ranked) == [0, 1]
    assert ranked[0].reason == "Tied with the other routes on risk and time"
    assert ranked[1].reason == "Same risk and time as the recommended route"


def test_single_route():
    ranked = rank_routes([RouteScore(0, miles(), 1.0, 3600)])
    assert ranked[0].reason == "Only route found"


def test_unknown_avg_risk_ranks_after_known():
    ranked = rank_routes([RouteScore(0, miles(), None, 3600), RouteScore(1, miles(), 3.0, 3600)])
    assert ids(ranked) == [1, 0]
