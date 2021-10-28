import pytest

from tesliper.glassware import (
    Bands,
    ElectronicActivities,
    Energies,
    FloatArray,
    Geometry,
    InfoArray,
    SingleSpectrum,
    Spectra,
    Transitions,
    VibrationalActivities,
)


@pytest.fixture(scope="module")
def arrays():
    yield [
        Energies("gib", [""], [1]),
        VibrationalActivities("iri", [""], [[1]], [[1]]),
        ElectronicActivities("vrot", [""], [[1]], [[1]]),
        Spectra("ir", [""], [[1, 2]], [1, 2]),
        SingleSpectrum("ir", [1, 2], [1, 2], averaged_by="gib"),
        InfoArray("command", [""], [""]),
        FloatArray("gibcorr", [""], [1]),
        Bands("freq", [""], [[1]]),
        Bands("wavelen", [""], [[1]]),
        InfoArray("stoichiometry", [""], [""]),
        Geometry("geometry", [""], [[[1, 2, 3]]], [[1]]),
        Transitions("transitions", [""], [[[(1, 2, 0.3)]]]),
    ]


@pytest.fixture(
    scope="module",
    params=[
        {"class": Transitions, "args": ["transitions", [""], [[[(1, 2, 0.3)]]]]},
        {"class": Geometry, "args": ["geometry", [""], [[[1, 2, 3]]], [[1]]]},
    ],
)
def forbidden_double_arrays(request):
    yield [
        request.param["class"](*request.param["args"]),
        request.param["class"](*request.param["args"]),
    ]
