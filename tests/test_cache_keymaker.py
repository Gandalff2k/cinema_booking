from core.cache.custom_key_maker import CustomKeyMaker


async def _sample(movie_id, other):
    return None


async def test_key_maker_includes_prefix_and_function():
    key = await CustomKeyMaker().make(function=_sample, prefix="movies")
    assert key.startswith("movies::")
    assert "_sample" in key


async def test_key_maker_is_stable():
    maker = CustomKeyMaker()
    a = await maker.make(function=_sample, prefix="movies")
    b = await maker.make(function=_sample, prefix="movies")
    assert a == b


async def test_key_maker_prefix_changes_key():
    maker = CustomKeyMaker()
    a = await maker.make(function=_sample, prefix="movies")
    b = await maker.make(function=_sample, prefix="shows")
    assert a != b
