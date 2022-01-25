import pytest

from tesliper.glassware import DataArray
from tesliper.glassware.arrays import SpectralActivities


def all_subclasses(cls):
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)]
    )


def get_all_genres_subclassing(cls):
    return {
        g
        for cls in all_subclasses(cls)
        if hasattr(cls, "associated_genres")
        for g in cls.associated_genres
    }


@pytest.fixture
def all_genres():
    return get_all_genres_subclassing(DataArray)


@pytest.fixture
def all_activities():
    return get_all_genres_subclassing(SpectralActivities)


@pytest.fixture(params=get_all_genres_subclassing(DataArray))
def any_genre(request):
    return request.param


@pytest.fixture(params=get_all_genres_subclassing(SpectralActivities))
def any_activity(request):
    return request.param
