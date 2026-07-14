from game.domain.leveling import grant_xp, kill_xp_reward, xp_to_next


def test_xp_to_next_grows_with_level():
    a = xp_to_next(1)
    b = xp_to_next(10)
    c = xp_to_next(50)
    assert a < b < c


def test_unlimited_level_ups():
    player = {
        "level": 1,
        "xp": 0,
        "max_hp": 100,
        "hp": 100,
        "max_mana": 50,
        "mana": 50,
        "bonus_atk": 5,
    }
    # dump huge xp
    grant_xp(player, 10_000_000)
    assert player["level"] > 20
    assert player["xp"] >= 0


def test_overlevel_gives_less_xp_than_underlevel():
    low = kill_xp_reward(player_level=20, monster_level=5)
    high = kill_xp_reward(player_level=5, monster_level=20)
    assert high > low
