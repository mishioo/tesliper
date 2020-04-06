# IMPORTS
from pathlib import Path
from typing import Union

import logging as lgg

from .. import glassware as gw


# LOGGER
logger = lgg.getLogger(__name__)
logger.setLevel(lgg.DEBUG)


# CLASSES
class Writer:

    _header = dict(
        freq="Frequencies",
        mass="Red. masses",
        frc="Frc consts",
        raman="Raman Activ",
        depolarp=r"Depolar \(P\)",
        depolaru=r"Depolar \(U\)",
        ramact="RamAct",
        depp="Dep-P",
        depu="Dep-U",
        alpha2="Alpha2",
        beta2="Beta2",
        alphag="AlphaG",
        gamma2="Gamma2",
        delta2="Delta2",
        cid1="CID1",
        raman2="Raman2",
        roa2="ROA2",
        cid2="CID2",
        raman3="Raman3",
        roa3="ROA3",
        cid3="CID3",
        rc180="RC180",
        rot="Rot. Str.",
        dip="Dip. Str.",
        roa1="ROA1",
        raman1="Raman1",
        ex_en="Excit. Energy",
        wave="Wavelenght",
        vrot="Rot.(velo)",
        lrot="Rot. (len)",
        vosc="Osc.(velo)",
        losc="Osc. (len)",
        iri="IR Int.",
        emang="E-M Angle",
        eemang="E-M Angle",
        zpe="Zero-point",
        ten="Thermal",
        ent="Enthalpy",
        gib="Gibbs",
        scf="SCF",
    )

    _formatters = dict(
        rot="{:> 10.4f}",
        dip="{:> 10.4f}",
        roa1="{:> 10.4f}",
        raman1="{:> 10.4f}",
        vrot="{:> 10.4f}",
        lrot="{:> 10.4f}",
        vosc="{:> 10.4f}",
        losc="{:> 10.4f}",
        iri="{:> 10.4f}",
        emang="{:> 10.4f}",
        eemang="{:> 10.4f}",
        zpe="{:> 13.4f}",
        ten="{:> 13.4f}",
        ent="{:> 13.4f}",
        gib="{:> 13.4f}",
        scf="{:> 13.4f}",
        ex_en="{:> 13.4f}",
        freq="{:> 10.2f}",
        wave="{:> 10.2f}",
        mass="{:> 11.4f}",
        frc="{:> 10.4f}",
        raman="{:> 11.4f}",
        depolarp="{:> 11.4f}",
        depolaru="{:> 11.4f}",
        ramact="{:> 10.4f}",
        depp="{:> 9.4f}",
        depu="{:> 9.4f}",
        alpha2="{:> 9.4f}",
        beta2="{:> 9.4f}",
        alphag="{:> 9.4f}",
        gamma2="{:> 9.4f}",
        delta2="{:> 9.4f}",
        cid1="{:> 8.3f}",
        raman2="{:> 8.3f}",
        roa2="{:> 8.3f}",
        cid2="{:> 8.3f}",
        raman3="{:> 8.3f}",
        roa3="{:> 8.3f}",
        cid3="{:> 8.3f}",
        rc180="{:> 8.3f}",
    )

    _excel_formats = dict(
        freq="0.0000",
        mass="0.0000",
        frc="0.0000",
        raman="0.0000",
        depolarp="0.0000",
        depolaru="0.0000",
        ramact="0.0000",
        depp="0.0000",
        depu="0.0000",
        alpha2="0.0000",
        beta2="0.0000",
        alphag="0.0000",
        gamma2="0.0000",
        delta2="0.0000",
        cid1="0.000",
        raman2="0.000",
        roa2="0.000",
        cid2="0.000",
        raman3="0.000",
        roa3="0.000",
        cid3="0.000",
        rc180="0.000",
        rot="0.0000",
        dip="0.0000",
        roa1="0.000",
        raman1="0.000",
        ex_en="0.0000",
        wave="0.0000",
        vrot="0.0000",
        lrot="0.0000",
        vosc="0.0000",
        losc="0.0000",
        iri="0.0000",
        emang="0.0000",
        eemang="0.0000",
        zpe="0.000000",
        ten="0.000000",
        ent="0.000000",
        gib="0.000000",
        scf="0.00000000",
    )

    energies_order = "zpe ten ent gib scf".split(" ")

    def __init__(self, destination: Union[str, Path]):
        self.destination = Path(destination)

    def distribute_data(self, data):
        distr = dict(
            energies=[],
            vibra=[],
            electr=[],
            other_bars=[],
            spectra=[],
            single=[],
            other=[],
            corrections={},
            frequencies=None,
            wavelenghts=None,
            stoichiometry=None,
        )
        for obj in data:
            if isinstance(obj, gw.Energies):
                distr["energies"].append(obj)
            elif obj.genre.endswith("corr"):
                distr["corrections"][obj.genre[:3]] = obj
            elif obj.genre == "freq":
                distr["frequencies"] = obj
            elif obj.genre == "wave":
                distr["wavelengths"] = obj
            elif obj.genre == "stoichiometry":
                distr["stoichiometry"] = obj
            elif isinstance(obj, gw.Bars):
                if obj.spectra_type == "vibra":
                    distr["vibra"].append(obj)
                elif obj.spectra_type == "electr":
                    distr["electr"].append(obj)
                else:
                    distr["other_bars"].append(obj)
            elif isinstance(obj, gw.SingleSpectrum):
                distr["single"].append(obj)
            elif isinstance(obj, gw.Spectra):
                distr["spectra"].append(obj)
            else:
                distr["other"].append(obj)
        return distr
