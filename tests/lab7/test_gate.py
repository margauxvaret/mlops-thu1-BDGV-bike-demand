from bike_demand.gate import decide, quality


def complete():
    return {
        name: ("accept", "ok")
        for name in ("integrity", "operation", "naive", "incumbent")
    }


def test_missing_control_fails_closed():
    checks = complete()
    del checks["operation"]
    assert decide(checks)[0] == "missing"


def test_invalid_result_is_never_accepted():
    checks = complete()
    checks["integrity"] = ("bogus", "invalid input")
    assert decide(checks)[0] == "invalid"


def test_equal_margin_passes():
    assert quality(9.0, 20.0, 10.0, False) == (True, True)


def test_naive_equality_fails_and_equivalence_is_not_improvement():
    assert quality(10.0, 10.0, 10.0, True) == (False, True)


def test_status_precedence():
    checks = complete()
    checks["naive"] = ("rejected", "measured")
    checks["incumbent"] = ("blocked", "absent")
    assert decide(checks)[0] == "blocked"
