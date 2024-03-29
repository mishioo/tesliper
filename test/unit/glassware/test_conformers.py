import pytest

from tesliper import glassware as gw
from tesliper.exceptions import TesliperError
from tesliper.glassware import conformers as cf


@pytest.fixture
def empty():
    return cf.Conformers()


@pytest.fixture
def single():
    return cf.Conformers(bla={"data": [1, 2, 3, 4]})


@pytest.fixture
def base():
    return {
        "normal_termination": True,
        "version": "Gaussian 09, Revision E.01",
        "command": "# opt freq=vcd B3LYP/Def2TZVP",
        "optimization_completed": True,
        "charge": 0,
        "multiplicity": 1,
        "input_geom": [],
        "stoichiometry": "CH3F",
        "last_read_atoms": (6, 1, 1, 1, 9),
        "last_read_geom": [],
        "freq": [1, 2, 3, 4, 5],
        "mass": [2, 1, 3, 2, 1],
        "iri": [27, 8, 569, 1, 3],
        "emang": [1.9, 1.4, 4.4, 1.1, 1.3],
        "wavelen": [231, 144, 137],
        "vdip": [0.0003, 0.008, 0.0022],
        "transitions": [
            ((20, 25, 0.1),),
            ((21, 25, -0.2), (23, 25, 0.6)),
            ((13, 25, -0.1), (15, 25, 0.3), (18, 25, -0.4)),
        ],
        "zpecorr": 0.5,
        "zpe": -200,
        "scf": 0,
    }


@pytest.fixture
def full(base):
    incom = {**base, "zpe": -260}
    del incom["scf"]
    return cf.Conformers(
        base=base,
        noopt={**base, "zpe": -210, "optimization_completed": False},
        imag={**base, "zpe": -220, "freq": [-1, 2, 3, 4, 5]},
        stoich={**base, "zpe": -230, "stoichiometry": "CH3F_other"},
        term={**base, "zpe": -240, "normal_termination": False},
        size={**base, "zpe": -250, "mass": [1, 2, 3]},
        incom=incom,
    )


@pytest.fixture
def jagged(full):
    full["size"]["excess"] = 1
    return full


def test_instantiation(empty, single):
    assert empty.kept == []
    assert empty.filenames == []
    assert single.kept == [True]
    assert single.filenames == ["bla"]
    assert isinstance(single["bla"], dict)


def test_setitem_with_dict(single):
    single["foo"] = {"data": [1, 2, 3, 4]}
    assert len(single) == 2
    assert single.kept == [True, True]
    assert single.filenames == ["bla", "foo"]


def test_setitem_with_zip(single):
    single["foo"] = zip(("data",), ([1, 2, 3, 4],))
    assert len(single) == 2
    assert single.kept == [True, True]
    assert single.filenames == ["bla", "foo"]


def test_setitem_with_tuple(single):
    single["foo"] = (("data", [1, 2, 3, 4]),)
    assert len(single) == 2
    assert single.kept == [True, True]
    assert single.filenames == ["bla", "foo"]


def test_setitem_with_invalid_type(single):
    with pytest.raises(TypeError):
        single["ham"] = (1, 2)
    with pytest.raises(TypeError):
        single["ham"] = 1


def test_setitem_with_invalid_value(single):
    with pytest.raises(ValueError):
        single["ham"] = ((1, 2, 3),)
    with pytest.raises(ValueError):
        single["ham"] = ((1,),)


def test_delitem_single(single):
    del single["bla"]
    assert single.kept == []
    assert single.filenames == []


def test_delitem_many(full):
    del full["imag"]
    assert full.kept == [True] * 6
    assert full.filenames == ["base", "noopt", "stoich", "term", "size", "incom"]
    assert [full._indices[k] for k in full.keys()] == list(range(6))


def test_update_with_kwargs(single):
    single.update(bla2={"data": [1, 2, 3, 4]})
    assert len(single) == 2
    assert single.kept == [True, True]
    assert single.filenames == ["bla", "bla2"]
    assert single._indices["bla2"] == 1
    assert single["bla2"] == {"data": [1, 2, 3, 4]}


def test_update_with_dict(single):
    single.update({"bla2": {"data": [1, 2, 3, 4]}})
    assert len(single) == 2
    assert single.kept == [True, True]
    assert single.filenames == ["bla", "bla2"]
    assert single._indices["bla2"] == 1
    assert single["bla2"] == {"data": [1, 2, 3, 4]}


def test_update_with_zip(single):
    single.update(zip(("bla2",), ({"data": [1, 2, 3, 4]},)))
    assert len(single) == 2
    assert single.kept == [True, True]
    assert single.filenames == ["bla", "bla2"]
    assert single._indices["bla2"] == 1
    assert single["bla2"] == {"data": [1, 2, 3, 4]}


def test_update_with_tuple(single):
    single.update((("bla2", {"data": [1, 2, 3, 4]}),))
    assert len(single) == 2
    assert single.kept == [True, True]
    assert single.filenames == ["bla", "bla2"]
    assert single._indices["bla2"] == 1
    assert single["bla2"] == {"data": [1, 2, 3, 4]}


def test_update_new(single):
    single.update(bla2={"data": [5, 6, 7, 8]})
    assert len(single) == 2
    assert single.kept == [True, True]
    assert single.filenames == ["bla", "bla2"]
    assert single._indices["bla2"] == 1
    assert single["bla2"] == {"data": [5, 6, 7, 8]}


def test_update_existing_with_new_data(single):
    single.update(bla={"data_new": "new"})
    assert len(single) == 1
    assert single.kept == [True]
    assert single.filenames == ["bla"]
    assert single._indices == {"bla": 0}
    assert single["bla"] == {"data": [1, 2, 3, 4], "data_new": "new"}


def test_update_existing_and_new(single):
    single.update(bla={"data_new": "new"}, bla2={"data": [1, 2, 3, 4]})
    assert len(single) == 2
    assert single.kept == [True, True]
    assert single.filenames == ["bla", "bla2"]
    assert single._indices == {"bla2": 1, "bla": 0}
    assert single["bla2"] == {"data": [1, 2, 3, 4]}
    assert single["bla"] == {"data": [1, 2, 3, 4], "data_new": "new"}


def test_update_repeated(single):
    single.update({"bla": {"data": "new"}}, bla={"other": "foo"})
    assert len(single) == 1
    assert single.kept == [True]
    assert single.filenames == ["bla"]
    assert single["bla"]["data"] == "new"
    assert single["bla"]["other"] == "foo"


def test_update_banned(single):
    with pytest.raises(TypeError):
        single.update(foo=7)
    with pytest.raises(TypeError):
        single.update({"foo": 7})


def test_pop_single(single):
    _ = single.pop("bla")
    assert not single
    assert not single.filenames
    assert not single._indices
    assert not single.kept


@pytest.mark.parametrize(
    "key", ["base", "noopt", "imag", "stoich", "term", "size", "incom"]
)
def test_pop(full, key):
    full.kept = [True, False, True, False, True, False, True]
    expected_filenames, expected_kept = zip(
        *[(n, k) for n, k in zip(full.filenames, full.kept) if n is not key]
    )
    _ = full.pop(key)
    assert key not in full
    assert full.filenames == list(expected_filenames)
    assert full.kept == list(expected_kept)
    assert full._indices == {n: i for i, n in enumerate(expected_filenames)}


@pytest.mark.parametrize("last", [True, False])
def test_popitem_single(single, last):
    pair = single.popitem(last=last)
    assert pair[0] == "bla"
    assert not single
    assert not single.filenames
    assert not single._indices
    assert not single.kept


@pytest.mark.parametrize("last", [True, False])
def test_popitem(full, last):
    full.kept = [True, False, True, False, True, False, True]
    expected_filenames = full.filenames[:-1] if last else full.filenames[1:]
    expected_kept = full.kept[:-1] if last else full.kept[1:]
    expected_key = full.filenames[-1] if last else full.filenames[0]
    pair = full.popitem(last=last)
    assert pair[0] == expected_key
    assert expected_key not in full
    assert full.filenames == list(expected_filenames)
    assert full.kept == list(expected_kept)
    assert full._indices == {n: i for i, n in enumerate(expected_filenames)}


@pytest.mark.parametrize("last", [True, False])
@pytest.mark.parametrize(
    "key", ["base", "noopt", "imag", "stoich", "term", "size", "incom"]
)
def test_move_to_end(full, key, last):
    full.move_to_end(key, last=last)
    assert full.filenames[0 if not last else -1] == key
    assert all(k == n for k, n in zip(full, full.filenames))
    assert all(full._indices[k] == i for i, k in enumerate(full.filenames))


def test_arrayed_default_parameter(full):
    zpe = full.arrayed("zpe")
    assert 298.15 == zpe.t


def test_arrayed_override_default_parameter(full):
    zpe = full.arrayed("zpe", t=300)
    assert 300 == zpe.t


def test_arrayed_unknown_kwarg_raises(full):
    with pytest.raises(TypeError):
        full.arrayed("zpe", unknown=1)


def test_arrayed_not_strict_ignores(full):
    # only checking if doesn't raise an exception
    _ = full.arrayed("zpe", strict=False, unknown=1)


def test_arrayd_empty(full):
    gib = full.arrayed("gib")
    assert [] == gib.filenames.tolist()
    assert [] == gib.values.tolist()
    assert 298.15 == gib.t


def test_arrayed_empty_spectral(full):
    arr = full.arrayed("ramact")
    assert [] == arr.filenames.tolist()
    assert [] == arr.values.tolist()
    assert [] == arr.frequencies.tolist()
    assert 298.15 == arr.t


def test_arrayed_types(full):
    zpe = full.arrayed("zpe")
    assert gw.Energies is type(zpe)
    normal_termination = full.arrayed("normal_termination")
    assert gw.BooleanArray is type(normal_termination)
    command = full.arrayed("command")
    assert gw.InfoArray is type(command)
    iri = full.arrayed("iri")
    assert gw.VibrationalActivities is type(iri)
    ramact = full.arrayed("ramact")
    assert gw.ScatteringActivities is type(ramact)
    vdip = full.arrayed("vdip")
    assert gw.ElectronicActivities is type(vdip)
    emang = full.arrayed("emang")
    assert gw.VibrationalData is type(emang)
    charge = full.arrayed("charge")
    assert gw.IntegerArray is type(charge)
    filenames = full.arrayed("filenames")
    assert gw.FilenamesArray is type(filenames)


def test_arrayed_trimmed(full):
    arr = full.arrayed("zpe")
    assert arr.values.shape == (len(full),)
    full.kept[2] = False
    arr = full.arrayed("zpe")
    assert arr.values.shape == (len(full) - 1,)
    assert list(arr.values) == [-200, -210, -230, -240, -250, -260]


def test_arrayed_unknown(full):
    with pytest.raises(ValueError):
        full.arrayed("nohave")


def test_arrayed_no_data(full):
    del full["incom"]["wavelen"]
    with pytest.raises(TesliperError):
        full.arrayed("vdip")


def test_trim_not_optimized(full):
    full.trim_not_optimized()
    assert [True, False, True, True, True, True, True] == full.kept


def test_trim_not_optimized_previously_trimmed(full):
    full.kept = [False, True, True, True, True, True, True]
    full.trim_not_optimized()
    assert [False, False, True, True, True, True, True] == full.kept


def test_trim_imaginary(full):
    full.trim_imaginary_frequencies()
    assert [True, True, False, True, True, True, True] == full.kept


def test_trim_imaginary_previously_trimmed(full):
    full.kept = [False, True, True, True, True, True, True]
    full.trim_imaginary_frequencies()
    assert [False, True, False, True, True, True, True] == full.kept


def test_trim_stoichiometry(full):
    full.trim_non_matching_stoichiometry()
    assert [True, True, True, False, True, True, True] == full.kept


def test_trim_stoichiometry_previously_trimmed(full):
    full.kept = [False, True, True, True, True, True, True]
    full.trim_non_matching_stoichiometry()
    assert [False, True, True, False, True, True, True] == full.kept


def test_trim_termination(full):
    full.trim_non_normal_termination()
    assert [True, True, True, True, False, True, True] == full.kept


def test_trim_termination_previously_trimmed(full):
    full.kept = [False, True, True, True, True, True, True]
    full.trim_non_normal_termination()
    assert [False, True, True, True, False, True, True] == full.kept


def test_trim_termination_missing(full):
    del full["base"]["normal_termination"]
    full.trim_non_normal_termination()
    assert [False, True, True, True, False, True, True] == full.kept


def test_trim_inconsistent_sizes(full):
    full.trim_inconsistent_sizes()
    assert [True, True, True, True, True, False, True] == full.kept


def test_trim_inconsistent_sizes_previously_trimmed(full):
    full.kept = [False, True, True, True, True, True, True]
    full.trim_inconsistent_sizes()
    assert [False, True, True, True, True, False, True] == full.kept


def test_trim_incomplete_default_previously_trimmed(full):
    full.kept = [False, True, True, True, True, True, True]
    full.trim_incomplete()
    assert [False, True, True, True, True, True, False] == full.kept


def test_trim_incomplete_default(full):
    full.trim_incomplete()
    assert [True, True, True, True, True, True, False] == full.kept
    full.kept = [True, True, True, True, True, True, True]
    del full["base"]["zpe"]
    full.trim_incomplete()
    assert [False, True, True, True, True, True, False] == full.kept


def test_trim_incomplete_wanted(full):
    del full["base"]["zpe"]
    full.trim_incomplete(wanted=["zpe"])
    assert [False, True, True, True, True, True, True] == full.kept
    full.kept = [True, True, True, True, True, True, True]
    full.trim_incomplete(wanted=["scf"])
    assert [True, True, True, True, True, True, False] == full.kept


def test_trim_incomplete_strict(full):
    m = gw.Conformers(
        one={"a": 1, "b": 2},
        two={"a": 1, "c": 3},
        three={"a": 1, "d": 3},
    )
    assert [True, True, True] == m.kept
    m.trim_incomplete(wanted=["a", "b", "c"])
    assert [True, False, False] == m.kept
    m.trim_incomplete(wanted=["a", "b", "c"], strict=True)
    assert [False, False, False] == m.kept


def test_trim_to_range_min(full):
    full.trim_to_range("zpe", minimum=-235)
    assert [True, True, True, True, False, False, False] == full.kept


def test_trim_to_range_previously_trimmed(full):
    full.kept = [False, True, True, True, True, True, True]
    full.trim_to_range("zpe", minimum=-235)
    assert [False, True, True, True, False, False, False] == full.kept


def test_trim_to_range_max(full):
    full.trim_to_range("zpe", maximum=-225)
    assert [False, False, False, True, True, True, True] == full.kept


def test_trim_to_range_min_max(full):
    full.trim_to_range("zpe", minimum=-255, maximum=-205)
    assert [False, True, True, True, True, True, False] == full.kept


def test_trim_to_range_errors(full):
    with pytest.raises(TypeError):
        full.trim_to_range("command")
    with pytest.raises(AttributeError):
        full.trim_to_range("zpe", attribute="bla")
    with pytest.raises(ValueError):
        full.trim_to_range("freq")


@pytest.mark.parametrize("trimmed", [True, False])  # if really empty or fully trimmed
@pytest.mark.parametrize(
    "method,args",
    [
        ("trim_not_optimized", []),
        ("trim_imaginary_frequencies", []),
        ("trim_non_matching_stoichiometry", []),
        ("trim_non_normal_termination", []),
        ("trim_inconsistent_sizes", []),
        ("trim_incomplete", []),
        ("trim_to_range", ["gib"]),
        ("trim_rmsd", [1, 1]),
    ],
)
def test_trim_empty(empty, single, method, args, trimmed):
    confs = empty if not trimmed else single
    if trimmed:
        confs.kept[0] = False
    callable = getattr(confs, method)
    callable(*args)
    assert confs.kept == ([False] if trimmed else [])


def test_select_all(full):
    full.kept = [True, False, True, False, True, False, False]
    assert not all(full.kept)
    full.select_all()
    assert all(full.kept)


def test_reject_all(full):
    full.kept = [True, False, True, False, True, False, False]
    full.reject_all()
    assert not all(full.kept)


def test_kept_raises(empty, full):
    with pytest.raises(TypeError):
        full.kept = 1
    with pytest.raises(TypeError):
        full.kept = {"bla": 1}
    with pytest.raises(KeyError):
        full.kept = ["zero"]
    with pytest.raises(ValueError):
        full.kept = [True] * 2
    with pytest.raises(ValueError):
        empty.kept = [True] * 2
    with pytest.raises(ValueError):
        full.kept = [True] * 20
    with pytest.raises(IndexError):
        full.kept = [200]
    with pytest.raises(TypeError):
        full.kept = [[]]


def test_kept(empty, full):
    assert [True] * 7 == full.kept
    full.kept = "imag stoich term".split(" ")
    assert [False, False, True, True, True, False, False] == full.kept
    full.kept = [1, 3, 5]
    assert [False, True, False, True, False, True, False] == full.kept
    full.kept = [True, False, False, True, False, False, True]
    assert [True, False, False, True, False, False, True] == full.kept
    full.kept = False
    assert [False] * 7 == full.kept
    full.kept = True
    assert [True] * 7 == full.kept
    assert [] == empty.kept
    empty.kept = []
    assert [] == empty.kept
    empty.kept = False
    assert [] == empty.kept


def test_by_index(full):
    for i, n in enumerate(full.filenames):
        assert full.by_index(i) is full[n]


def test_index_key(full):
    for i in range(len(full)):
        assert full.index_of(full.key_of(i)) == i


@pytest.mark.parametrize(
    "genre,output",
    [("freq", True), ("scf", True), ("excess", True), ("nohave", False)],
)
def test_has_genre(jagged, genre, output):
    assert jagged.has_genre(genre) == output


@pytest.mark.parametrize(
    "genre,output",
    [("freq", True), ("scf", True), ("excess", False), ("nohave", False)],
)
def test_has_genre_trimmed(jagged, genre, output):
    jagged.kept = list(range(4))
    assert jagged.has_genre(genre, ignore_trimming=False) == output


@pytest.mark.parametrize(
    "genre,output",
    [("freq", True), ("scf", True), ("excess", True), ("nohave", False)],
)
def test_has_genre_untrimmed(jagged, genre, output):
    jagged.kept = list(range(4))
    assert jagged.has_genre(genre, ignore_trimming=True) == output


@pytest.mark.parametrize(
    "genre,output",
    [
        (["freq", "nohave"], True),
        (["scf", "nohave"], True),
        (["excess", "nohave"], True),
        (["nohave", "alsonohave"], False),
    ],
)
def test_has_any_genre(jagged, genre, output):
    assert jagged.has_any_genre(genre) == output


@pytest.mark.parametrize(
    "genre,output",
    [
        (["freq", "nohave"], True),
        (["scf", "nohave"], True),
        (["excess", "nohave"], False),
        (["nohave", "alsonohave"], False),
    ],
)
def test_has_any_genre_trimmed(jagged, genre, output):
    jagged.kept = list(range(4))
    assert jagged.has_any_genre(genre, ignore_trimming=False) == output


@pytest.mark.parametrize(
    "genre,output",
    [
        (["freq", "nohave"], True),
        (["scf", "nohave"], True),
        (["excess", "nohave"], True),
        (["nohave", "alsonohave"], False),
    ],
)
def test_has_any_genre_untrimmed(jagged, genre, output):
    jagged.kept = list(range(4))
    assert jagged.has_any_genre(genre, ignore_trimming=True) == output


@pytest.mark.parametrize(
    "genre,output",
    [
        (["freq", "iri"], True),
        (["scf", "iri"], False),
        (["excess", "iri"], False),
        (["nohave", "iri"], False),
    ],
)
def test_all_have_genres(jagged, genre, output):
    assert jagged.all_have_genres(genre) == output


@pytest.mark.parametrize(
    "genre,output",
    [
        (["freq", "iri"], True),
        (["scf", "iri"], True),
        (["excess", "iri"], False),
        (["nohave", "iri"], False),
    ],
)
def test_all_have_genres_trimmed(jagged, genre, output):
    jagged.kept = list(range(4))
    assert jagged.all_have_genres(genre, ignore_trimming=False) == output


@pytest.mark.parametrize(
    "genre,output",
    [
        (["freq", "iri"], True),
        (["scf", "iri"], False),
        (["excess", "iri"], False),
        (["nohave", "iri"], False),
    ],
)
def test_all_have_genres_untrimmed(jagged, genre, output):
    jagged.kept = list(range(4))
    assert jagged.all_have_genres(genre, ignore_trimming=True) == output


def test_inconsistency_allowed_context(single):
    with single.inconsistency_allowed:
        assert single.allow_data_inconsistency
    assert not single.allow_data_inconsistency


def test_trimmed_to_context(full):
    with full.trimmed_to("imag stoich term".split(" ")):
        assert [False, False, True, True, True, False, False] == full.kept
    assert [True] * 7 == full.kept


def test_untrimmed_context(full):
    full.kept = [False, False, True, True, True, False, False]
    with full.untrimmed:
        assert [True] * 7 == full.kept
    assert full.kept == [False, False, True, True, True, False, False]


# TODO: add tests for View objects
