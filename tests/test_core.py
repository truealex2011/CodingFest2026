import random

import pytest

from core.db import RecordsDB
from core.shagai import (DICE_COUNT, FINISH, START, Race, Rider, Side, calc_score,
                         horses_in, throw)
from core.validation import NameError_, validate_name

H, S, G, C = Side.MORIN, Side.HONIN, Side.YAMAAN, Side.TEMEEN


def test_throw_has_five_bones():
    assert len(throw(random.Random(1))) == DICE_COUNT


def test_horses_count():
    assert horses_in([H, H, S, G, C]) == 2
    assert horses_in([S, S, S, G, C]) == 0


def test_no_horse_stays():
    race = Race([Rider("A"), Rider("B")])
    t = race.play_turn([S, S, G, G, C])
    assert t.steps == 0 and t.new_position == START
    assert race.current_rider.name == "B"


def test_horses_move_forward():
    race = Race([Rider("A")])
    t = race.play_turn([H, H, H, S, S])
    assert t.new_position == START + 3


def test_winner_after_passing_12():
    a = Rider("A", position=FINISH - 2)
    race = Race([a, Rider("B")])
    race.play_turn([H, H, H, S, S])
    assert race.winner is a and a.position == FINISH and race.over
    with pytest.raises(RuntimeError):
        race.play_turn()


def test_full_race_terminates():
    race = Race([Rider("A"), Rider("B"), Rider("C")], rng=random.Random(7))
    for _ in range(10_000):
        if race.over:
            break
        race.play_turn()
    assert race.over and race.place_of(race.winner) == 1


def test_wrong_dice_count():
    with pytest.raises(ValueError):
        Race([Rider("A")]).play_turn([H, H])


def test_score():
    assert calc_score(False, 0, 10, 0) == 0
    assert calc_score(True, 12, 10, 0) == 600 + 400 + 200
    assert calc_score(True, 12, 10, 2) == 1440


@pytest.mark.parametrize("bad", ["", "   ", None, "x" * 21, "Бат<script>", "123"])
def test_bad_names(bad):
    with pytest.raises(NameError_):
        validate_name(bad)


def test_good_names():
    assert validate_name("  Баатар   Дорж ") == "Баатар Дорж"
    assert validate_name("Сэсэгмаа-2") == "Сэсэгмаа-2"
    assert validate_name("Һүхэ") == "Һүхэ"


def test_db_crud_and_filter():
    db = RecordsDB()
    a = db.add("Баатар", 900, 15, 1, 3)
    db.add("Сэсэг", 500, 20, 2, 3)
    db.add("баир", 100, 22, 3, 3)
    assert [r.name for r in db.list()] == ["Баатар", "Сэсэг", "баир"]
    assert [r.name for r in db.list("БА")] == ["Баатар", "баир"]
    assert db.list("нет такого") == []
    db.rename(a, "Батор")
    assert db.list()[0].name == "Батор"
    with pytest.raises(NameError_):
        db.rename(a, "  ")
    db.delete(a)
    assert db.rank_of(a) is None and len(db.list()) == 2
    with pytest.raises(KeyError):
        db.delete(a)


def test_db_injection_safe():
    db = RecordsDB()
    db.add("Баатар", 1, 1, 1, 1)
    assert db.list("'; DROP TABLE records; --") == []
    assert len(db.list()) == 1


def test_export(tmp_path):
    db = RecordsDB()
    db.add("Баатар", 1, 1, 1, 1)
    p = tmp_path / "r.csv"
    assert db.export_csv(p) == 1
    assert "Баатар" in p.read_text(encoding="utf-8-sig")


from core import achievements as A


def test_throw_achievements():
    assert A.for_throw(0) == []
    assert A.for_throw(1) == ["first_horse"]
    assert set(A.for_throw(3)) == {"first_horse", "herd"}


def test_race_achievements():
    got = A.for_race(won=True, throws=12, quiz_ok=3, quiz_asked=3, hotseat=True, races_played=10)
    assert set(got) == {"winner", "fast", "scholar", "friends", "veteran"}
    assert A.for_race(won=False, throws=30, quiz_ok=1, quiz_asked=3, hotseat=False, races_played=1) == []
    assert "scholar" not in A.for_race(False, 5, 0, 0, False, 1)


def test_harbaha_achievements():
    assert A.for_harbaha(2, False) == []
    assert set(A.for_harbaha(3, True)) == {"sniper", "clean"}


def test_unlock_once_and_case_insensitive():
    db = RecordsDB(":memory:")
    assert db.unlock("Баир", "winner") is True
    assert db.unlock("баир", "winner") is False
    assert set(db.achievements("БАИР")) == {"winner"}


def test_player_records_and_harbaha():
    db = RecordsDB(":memory:")
    db.add("Баир", 100, 10, 1, 2)
    db.add("Баирма", 50, 10, 2, 2)
    db.add("баир", 300, 9, 1, 2)
    assert [r.score for r in db.player_records("БАИР")] == [100, 300]
    db.add_harbaha("Аюна", 400, 4)
    db.add_harbaha("Аюна", 250, 2)
    assert db.harbaha_best("аюна") == 400
    assert db.harbaha_top(1) == [("Аюна", 400, 4)]
    with pytest.raises(NameError_):
        db.add_harbaha("", 10, 1)


from core import harbaha as HB


def test_harbaha_judge():
    assert HB.judge(Side.HONIN, Side.HONIN) == HB.HIT
    assert HB.judge(Side.HONIN, Side.MORIN) == HB.FOUL
    assert HB.judge(Side.HONIN, None) == HB.MISS


def test_harbaha_scatter_has_pairs():
    rng = random.Random(4)
    for _ in range(50):
        s = HB.scatter(rng)
        assert len(s) == HB.BONES and HB.has_pairs(s)
    assert not HB.has_pairs([Side.HONIN, Side.MORIN, Side.YAMAAN])


def test_harbaha_points():
    assert [HB.hit_points(c) for c in (1, 2, 5, 9)] == [100, 200, 500, 500]
    assert HB.final_bonus(True, 2) == 500
    assert HB.final_bonus(False, 3) == 0


def test_plural_forms():
    from ui.widgets import plural, throws_txt
    assert [plural(n, "бросок", "броска", "бросков") for n in (1, 2, 5, 11, 21, 22, 112)] ==         ["бросок", "броска", "бросков", "бросков", "бросок", "броска", "бросков"]
    assert throws_txt(1) == "1 бросок"


from core.shagai import QUICK_LENGTH


def test_quick_race_finishes_at_six():
    r = Rider("Аюна", is_human=True)
    race = Race([r], length=QUICK_LENGTH)
    race.play_turn([H, H, H, S, S])
    assert not race.over and r.progress == 3
    race.play_turn([H, H, H, H, S])
    assert race.over and race.winner is r and r.progress == QUICK_LENGTH


def test_quick_race_scores_less_than_classic():
    classic = calc_score(True, 12, 20, 2)
    quick = calc_score(True, 6, 10, 2, length=QUICK_LENGTH)
    assert quick < classic
    assert calc_score(True, 12, 10, 0) == calc_score(True, 12, 10, 0, length=12)


def test_fast_badge_only_in_classic():
    assert "fast" in A.for_race(True, 8, 0, 0, False, 1, classic=True)
    assert "fast" not in A.for_race(True, 8, 0, 0, False, 1, classic=False)
