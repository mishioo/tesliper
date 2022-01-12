.. _available genres:

Available data genres
=====================

:freq: *list of floats*; available from freq job
    
    harmonic vibrational frequencies (cm^-1)

:mass: *list of floats*; available from freq job
    
    reduced masses (AMU)

:frc: *list of floats*; available from freq job
    
    force constants (mDyne/A)

:iri: *list of floats*; available from freq job
    
    IR intensities (KM/mole)

:dip: *list of floats*; available from freq=VCD job
    
    dipole strengths (10**-40 esu**2-cm**2)

:rot: *list of floats*; available from freq=VCD job
    
    rotational strengths (10**-44 esu**2-cm**2)

:emang: *list of floats*; available from freq=VCD job
    
    E-M angle = Angle between electric and magnetic dipole transition moments (deg)

:depolarp: *list of floats*; available from freq=Raman job
    
    depolarization ratios for plane incident light

:depolaru: *list of floats*; available from freq=Raman job
    
    depolarization ratios for unpolarized incident light

:ramanactiv: *list of floats*; available from freq=Raman job
    
    Raman scattering activities (A**4/AMU)

:ramact: *list of floats*; available from freq=ROA job
    
    Raman scattering activities (A**4/AMU)

:depp: *list of floats*; available from freq=ROA job
    
    depolarization ratios for plane incident light

:depu: *list of floats*; available from freq=ROA job
    
    depolarization ratios for unpolarized incident light

:alpha2: *list of floats*; available from freq=ROA job
    
    Raman invariants Alpha2 = alpha**2 (A**4/AMU)

:beta2: *list of floats*; available from freq=ROA job
    
    Raman invariants Beta2 = beta(alpha)**2 (A**4/AMU)

:alphag: *list of floats*; available from freq=ROA job
    
    ROA invariants AlphaG = alphaG'(10**4 A**5/AMU)

:gamma2: *list of floats*; available from freq=ROA job
    
    ROA invariants Gamma2 = beta(G')**2 (10**4 A**5/AMU)

:delta2: *list of floats*; available from freq=ROA job
    
    ROA invariants Delta2 = beta(A)**2, (10**4 A**5/AMU)

:raman1: *list of floats*; available from freq=ROA job
    
    Far-From-Resonance Raman intensities =ICPu/SCPu(180) (K)

:roa1: *list of floats*; available from freq=ROA job
    
    ROA intensities =ICPu/SCPu(180) (10**4 K)

:cid1: *list of floats*; available from freq=ROA job
    
    CID=(ROA/Raman)*10**4 =ICPu/SCPu(180)

:raman2: *list of floats*; available from freq=ROA job
    
    Far-From-Resonance Raman intensities =ICPd/SCPd(90) (K)

:roa2: *list of floats*; available from freq=ROA job
    
    ROA intensities =ICPd/SCPd(90) (10**4 K)

:cid2: *list of floats*; available from freq=ROA job
    
    CID=(ROA/Raman)*10**4 =ICPd/SCPd(90)

:raman3: *list of floats*; available from freq=ROA job
    
    Far-From-Resonance Raman intensities =DCPI(180) (K)

:roa3: *list of floats*; available from freq=ROA job
    
    ROA intensities =DCPI(180) (10**4 K)

:cid3: *list of floats*; available from freq=ROA job
    
    CID=(ROA/Raman)*10**4 =DCPI(180)

:rc180: *list of floats*; available from freq=ROA job
    
    RC180 = degree of circularity

:wavelen: *list of floats*; available from td job
    
    excitation energies (nm)

:ex_en: *list of floats*; available from td job
    
    excitation energies (eV)

:eemang: *list of floats*; available from td job
    
    E-M angle = Angle between electric and magnetic dipole transition moments (deg)

:vdip: *list of floats*; available from td job
    
    dipole strengths (velocity)

:ldip: *list of floats*; available from td job
    
    dipole strengths (length)

:vrot: *list of floats*; available from td job
    
    rotatory strengths (velocity) in cgs (10**-40 erg-esu-cm/Gauss)

:lrot: *list of floats*; available from td job
    
    rotatory strengths (length) in cgs (10**-40 erg-esu-cm/Gauss)

:vosc: *list of floats*; available from td job
    
    oscillator strengths

:losc: *list of floats*; available from td job
    
    oscillator strengths

:transitions: *list of lists of lists of (int, int, float)*; available from td job
    
    transitions (first to second) and their coefficients (third)

:scf: *float*; always available
    
    SCF energy

:zpe: *float*; available from freq job
    
    Sum of electronic and zero-point Energies (Hartree/Particle)

:ten: *float*; available from freq job
    
    Sum of electronic and thermal Energies (Hartree/Particle)

:ent: *float*; available from freq job
    
    Sum of electronic and thermal Enthalpies (Hartree/Particle)

:gib: *float*; available from freq job
    
    Sum of electronic and thermal Free Energies (Hartree/Particle)

:zpecorr: *float*; available from freq job
    
    Zero-point correction (Hartree/Particle)

:tencorr: *float*; available from freq job
    
    Thermal correction to Energy (Hartree/Particle)

:entcorr: *float*; available from freq job
    
    Thermal correction to Enthalpy (Hartree/Particle)

:gibcorr: *float*; available from freq job
    
    Thermal correction to Gibbs Free Energy (Hartree/Particle)

:command: *str*; always available
    
    command used for calculations

:normal_termination: *bool*; always available
    
    true if Gaussian job seem to exit normally, false otherwise

:optimization_completed: *bool*; available from opt job
    
    true if structure optimization was performed successfully

:version: *str*; always available
    
    version of Gaussian software used

:charge: *int*; always available
    
    molecule's charge

:multiplicity: *int*; always available
    
    molecule's spin multiplicity

:input_atoms: *list of str*; always available
    
    input atoms as a list of atoms' symbols

:input_geom: *list of lists of floats*; always available
    
    input geometry as X, Y, Z coordinates of atoms

:stoichiometry: *str*; always available
    
    molecule's stoichiometry

:last_read_atoms: *list of ints*; always available
    
    molecule's atoms as atomic numbers

:last_read_geom: *list of lists of floats*; always available
    
    molecule's geometry (last one found in file) as X, Y, Z coordinates of atoms

:optimized_atoms: *list of ints*; available from successful opt job
    
    molecule's atoms read from optimized geometry as atomic numbers

:optimized_geom: *list of lists of floats*; available from successful opt job
    
    optimized geometry as X, Y, Z coordinates of atoms

