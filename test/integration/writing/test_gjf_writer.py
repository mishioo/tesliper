from itertools import zip_longest

import pytest

from tesliper.writing.gjf_writer import GjfWriter
from tesliper.glassware import arrays as ar


meoh0 = """# hf/sto-3g

No information provided.

0 1
 C   -0.67991631   0.47594142   0.00000000
 H   -0.32326188  -0.53286858   0.00000000
 H   -0.32324347   0.98033961   0.87365150
 H   -1.74991631   0.47595461   0.00000000
 O   -0.20324139   1.15004368  -1.16759033
 H   -0.52444619   2.05471256  -1.16889301

"""

meoh1 = """# hf/sto-3g

No information provided.

0 1
 C   -0.68000778   0.47593315   0.00011979
 H   -1.20068109  -0.41315771   0.28876620
 H    0.14875250   0.21684353  -0.62512333
 H   -1.34450706   1.11989523  -0.53714509
 O   -0.20368106   1.14979513   1.16799088
 H   -0.94726301   1.51890557   1.65011469

"""


@pytest.fixture
def filenames():
    return ["meoh0", "meoh1"]


@pytest.fixture
def geometry(filenames):
    values = [
        [
            [-0.67991631, 0.47594142, 0.00000000],
            [-0.32326188, -0.53286858, 0.00000000],
            [-0.32324347, 0.98033961, 0.87365150],
            [-1.74991631, 0.47595461, 0.00000000],
            [-0.20324139, 1.15004368, -1.16759033],
            [-0.52444619, 2.05471256, -1.16889301],
        ],
        [
            [-0.68000778, 0.47593315, 0.00011979],
            [-1.20068109, -0.41315771, 0.28876620],
            [0.14875250, 0.21684353, -0.62512333],
            [-1.34450706, 1.11989523, -0.53714509],
            [-0.20368106, 1.14979513, 1.16799088],
            [-0.94726301, 1.51890557, 1.65011469],
        ],
    ]
    molecule_atoms = ["C H H H O H".split()]
    return ar.Geometry(
        genre="geometry",
        filenames=filenames,
        values=values,
        molecule_atoms=molecule_atoms,
    )


@pytest.fixture
def charge(filenames,):
    values = [0] * len(filenames)
    return ar.IntegerArray(genre="charge", filenames=filenames, values=values)


@pytest.fixture
def multiplicity(filenames,):
    values = [1] * len(filenames)
    return ar.IntegerArray(genre="multiplicity", filenames=filenames, values=values)


@pytest.fixture(params=["values", 0, [0]])
def altcharge(filenames, request):
    if not isinstance(request.param, str):
        return request.param
    if request.param == "values":
        return [0] * len(filenames)


@pytest.fixture(params=["values", 1, [1]])
def altmultiplicity(filenames, request):
    if not isinstance(request.param, str):
        return request.param
    if request.param == "values":
        return [1] * len(filenames)


@pytest.fixture
def gjfwriter(tmp_path):
    return GjfWriter(tmp_path, route="hf/sto-3g")


def test_basic(tmp_path, gjfwriter, geometry, charge, multiplicity, filenames):
    gjfwriter.write(geometry, charge, multiplicity)
    assert len(list(tmp_path.iterdir())) == 2
    assert {f.name for f in tmp_path.iterdir()} == {f"{f}.gjf" for f in filenames}
    assert tmp_path.joinpath(filenames[0] + ".gjf").open("r").read() == meoh0
    assert tmp_path.joinpath(filenames[1] + ".gjf").open("r").read() == meoh1


def test_alt_args(tmp_path, gjfwriter, geometry, altcharge, altmultiplicity, filenames):
    gjfwriter.write(geometry, altcharge, altmultiplicity)
    assert len(list(tmp_path.iterdir())) == 2
    assert {f.name for f in tmp_path.iterdir()} == {f"{f}.gjf" for f in filenames}
    assert tmp_path.joinpath(filenames[0] + ".gjf").open("r").read() == meoh0
    assert tmp_path.joinpath(filenames[1] + ".gjf").open("r").read() == meoh1


@pytest.mark.parametrize(
    "link0,expline",
    (
        ({"mem": "10GB"}, "%Mem=10GB\n"),
        ({"nosave": True}, "%NoSave\n"),
        ({"mem": "10GB", "nosave": False}, "%Mem=10GB\n"),
    ),
)
def test_link0(tmp_path, gjfwriter, link0, expline):
    gjfwriter.link0 = link0
    with tmp_path.joinpath("test.gjf").open("w") as file:
        gjfwriter._write_conformer(file, [[1, 1, 1]], [1], 0, 1)
    expected = [
        expline,
        "# hf/sto-3g\n",
        "\n",
        "No information provided.\n",
        "\n",
        "0 1\n",
        " H    1.00000000   1.00000000   1.00000000\n",
        "\n",
    ]
    with tmp_path.joinpath("test.gjf").open("r") as file:
        for line, exp in zip_longest(file, expected, fillvalue=None):
            assert line == exp


def test_wrong_route_type(gjfwriter):
    with pytest.raises(TypeError):
        gjfwriter.route = 123


def test_post_spec(tmp_path, gjfwriter):
    gjfwriter.post_spec = "some post specs 123"
    with tmp_path.joinpath("test.gjf").open("w") as file:
        gjfwriter._write_conformer(file, [[1, 1, 1]], [1], 0, 1)
    with tmp_path.joinpath("test.gjf").open("r") as file:
        output = file.read()
    assert output.endswith(f"\n\n{gjfwriter.post_spec}\n\n")
    assert not output.endswith(f"\n\n\n{gjfwriter.post_spec}\n\n")
