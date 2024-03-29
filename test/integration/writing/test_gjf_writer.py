from itertools import zip_longest

import pytest

from tesliper.glassware import arrays as ar
from tesliper.writing.gjf_writer import GjfWriter

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
    atoms = ["C H H H O H".split()]
    return ar.Geometry(
        genre="last_read_geom",
        filenames=filenames,
        values=values,
        atoms=atoms,
    )


@pytest.fixture
def charge(filenames):
    values = [0] * len(filenames)
    return ar.IntegerArray(genre="charge", filenames=filenames, values=values)


@pytest.fixture
def multiplicity(filenames):
    values = [1] * len(filenames)
    return ar.IntegerArray(genre="multiplicity", filenames=filenames, values=values)


@pytest.fixture(params=["values", 0, [0]])
def alt_charge(filenames, request):
    if not isinstance(request.param, str):
        return request.param
    if request.param == "values":
        return [0] * len(filenames)


@pytest.fixture(params=["values", 1, [1]])
def alt_multiplicity(filenames, request):
    if not isinstance(request.param, str):
        return request.param
    if request.param == "values":
        return [1] * len(filenames)


@pytest.fixture
def gjfwriter(tmp_path):
    return GjfWriter(tmp_path, route="hf/sto-3g")


def assert_output_ok(path, names):
    assert len(list(path.iterdir())) == 2
    assert {f.name for f in path.iterdir()} == {f"{f}.gjf" for f in names}
    for name in names:
        with path.joinpath(name + ".gjf").open("r") as file:
            assert file.read() == globals()[name]


def test_basic(tmp_path, gjfwriter, geometry, charge, multiplicity, filenames):
    gjfwriter.geometry(geometry, charge, multiplicity)
    assert_output_ok(tmp_path, filenames)


def test_default_args(tmp_path, gjfwriter, geometry, filenames):
    gjfwriter.geometry(geometry)
    assert_output_ok(tmp_path, filenames)


def test_alt_charge(tmp_path, gjfwriter, geometry, alt_charge, filenames):
    gjfwriter.geometry(geometry, alt_charge)
    assert_output_ok(tmp_path, filenames)


def test_alt_multiplicity(tmp_path, gjfwriter, geometry, alt_multiplicity, filenames):
    gjfwriter.geometry(geometry, multiplicity=alt_multiplicity)
    assert_output_ok(tmp_path, filenames)


def test_parametrized(tmp_path, gjfwriter, geometry, charge, multiplicity, filenames):
    gjfwriter.link0 = {"Chk": "link/to/${conf}.ext"}
    gjfwriter.geometry(geometry, charge, multiplicity)
    for name in filenames:
        with tmp_path.joinpath(name + ".gjf").open("r") as file:
            assert file.read().startswith(f"%Chk=link/to/{name}.ext")


@pytest.mark.parametrize(
    "link0,expline",
    (
        ({"mem": "10GB"}, "%Mem=10GB\n"),
        ({"Mem": "10GB"}, "%Mem=10GB\n"),
        ({"nosave": True}, "%NoSave\n"),
        ({"mem": "10GB", "nosave": False}, "%Mem=10GB\n"),
    ),
)
def test_link0(tmp_path, gjfwriter, link0, expline):
    gjfwriter.link0 = link0
    with tmp_path.joinpath("test.gjf").open("w") as file:
        gjfwriter._write_conformer(file, [[1, 1, 1]], [1], 0, 1, {})
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


@pytest.mark.parametrize("param", GjfWriter._parametrized)
def test_link0_parametrized(tmp_path, gjfwriter, param):
    gjfwriter.link0 = {param: "link/to/${conf}.ext"}
    with tmp_path.joinpath("test.gjf").open("w") as file:
        gjfwriter._write_conformer(file, [[1, 1, 1]], [1], 0, 1, {"conf": "test"})
    with tmp_path.joinpath("test.gjf").open("r") as file:
        cont = file.read()
    assert cont.startswith(f"%{gjfwriter._link0_commands[param]}=link/to/test.ext")


def test_wrong_route_type(gjfwriter):
    with pytest.raises(TypeError):
        gjfwriter.route = 123


def test_post_spec(tmp_path, gjfwriter):
    gjfwriter.post_spec = "some post specs 123"
    with tmp_path.joinpath("test.gjf").open("w") as file:
        gjfwriter._write_conformer(file, [[1, 1, 1]], [1], 0, 1, {})
    with tmp_path.joinpath("test.gjf").open("r") as file:
        output = file.read()
    assert output.endswith(f"\n\n{gjfwriter.post_spec}\n\n")
    assert not output.endswith(f"\n\n\n{gjfwriter.post_spec}\n\n")
