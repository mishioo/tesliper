import pytest

from tesliper.glassware import DataArray


def all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)]
    )


all_genres_ = {
    g
    for cls in all_subclasses(DataArray)
    if hasattr(cls, "associated_genres")
    for g in cls.associated_genres
}


@pytest.fixture
def all_genres():
    return all_genres_.copy()


@pytest.fixture(params=all_genres_)
def any_genre(request):
    return request.param
