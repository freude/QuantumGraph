import numpy as np
import scipy.linalg as linalg


def pole_maker(Emin, ChemPot, kT, reltol):
    """This is an alternate pole summation method implemented by Areshkin-Nikolic [CITE].
    Similar to the continued-fraction representation of Ozaki, this method allows for
    efficient computation of the density matrix by complex pole summation. Both methods
    approximate the Fermi-Dirac distribution function so that it is more easily manipulable.

    One of the exciting uses of this method is for finite differences, and the computation
    of quasi-equilibrium solutions for use in efficient non-equilibrium density matrices
    as the user can reuse certain poles but with different weights for little extra cost.

    What A-N does is replaces f(E,mu) with one that approximates it on the real line:
    f(E,mu,kT) -> f(E,1j*mu_im,1j*kT_im)*( f(E,mu,kT) - f(Emin, mu_re,kT_re) ) but has
    drastic changes in the upper complex plane. By judicious choice of mu_im to be at
    least p*kT away from the real line and mu_re to be at least p*kT away from the
    minimum eigenvalue Emin, this gives a controlled relative error of e^-p.

    This function automatically switches from first order to second order when
    appropriate. This is when the interval divided by the temperature exceeds 10^3.
    To-do: add third order method.

     Parameters
    ----------
    Emin    : scalar (dtype=numpy.float)
           Minimum occupied state, e.g. a band edge.
    ChemPot : scalar (dtype=numpy.float)
           The chemical potential
    kT      : scalar (dtype=numpy.float)
           The temperature (in units of energy)
    reltol : scalar (dtype=numpy.float)
           The desired relative tolerance. p = -np.log(reltol)

    """
    p = -np.log(reltol)  # Compute the exponent for the relative tolerance desired.

    # When energy exceeds 10^3, switch to second order poles.
    z = (ChemPot - Emin) / kT

    if z < 10 ** 3:
        poles, residues = pole_order_one(Emin, ChemPot, kT, p)
    else:
        poles, residues = pole_order_two(Emin, ChemPot, kT, p)

    return poles, residues


def pole_order_one(Emin, ChemPot, kT, p):
    poles = 1
    residues = 1

    return poles, residues


def pole_order_two(Emin, ChemPot, kT, p):
    poles = 1
    residues = 1

    return poles, residues


def pole_finite_difference(muL, muR, kT, reltol):
    """
    For computing the finite difference derivative using pole summation, see Vaitkus thesis.

    By using 2x one-sided differences, we can get the forwards, backwards, and centred
    first derivatives and the centred second derivative. The poles will be written as a vector
    containing all points, and the residues will be two vectors containing the poles for the
    backwards and forward differences respectively as (f_mid-f_min) and (f_max-f_mid).

    This choice is so that the user need compute the poles only once and
    can carry out whichever residues you like using the following recipes:

    h = np.abs(muR - muC)

    Forward  1st = ( (f_max-f_mid)                 ) / (  h)
    Centred  1st = ( (f_max-f_mid) + (f_mid-f_min) ) / (2*h)
    Backward 1st = ( (f_mid-f_min)                 ) / (  h)
    Centred  2nd = ( (f_max-f_mid) - (f_mid-f_min) ) / (2*h)

    Parameters
    ----------
    muL    : scalar (dtype=numpy.float)
           Left chemical potential
    muR    : scalar (dtype=numpy.float)
           Right chemical potential
    kT     : scalar (dtype=numpy.float)
           The temperature (in units of energy)
    reltol : scalar (dtype=numpy.float)
           The desired relative tolerance. p = -np.log(reltol)

    """

    p = -np.log(reltol)  # Value of p that gives desired relative tolerance.

    muMin = np.min([muL, muR])
    muMax = np.max([muL, muR])
    muMid = 0.5 * (muMin + muMax)

    kTIm = np.sqrt((muMax - muMin + 2 * p * kT) / (6 * p / kT))  # Analytical solution for minimum pole number
    # Correcting temperature so that p*kTIm will be directly between the poles from the other funcs.
    kTIm = (2 * np.pi * kT / p) * np.ceil((p * kTIm) / (2 * np.pi * kT))
    muIm = p * kTIm  # Where muIm should be to get e^-p error

    # Four pole branches
    #   :  :  :
    # - - - - - - D
    #   :  :  :
    #   :  :  :
    #   A  B  C

    dummyindex = np.arange(-500, 500 + 1)  # Integers from -500 to 500 inclusive,.
    # Need to make a more reasonable guess for valid integers, real line is easy, imag is hard

    # Residues for Fermi-Dirac are simply -kT, residue theorem multiplies
    # by 2*pi*i, then the windowing function multiplies in its own factor:

    # Branch A poles:
    poleA = muMin + 1j * np.pi * kT * (2 * dummyindex + 1)  # Analytical pole location from definition of fermi-fun
    # Residues for left
    resA_L = (2j * np.pi * kT) * fermi_fun(poleA, 1j * muIm, 1j * kTIm)
    # Residues for right
    resA_R = 0 * poleA
    # Determine which to trim, they must have magnitude over tol and be in upper complex plane
    zA = (np.abs(resA_L) >= np.exp(-p) * kT) & (np.imag(poleA) > 0)
    poleA = poleA[zA]
    resA_L = resA_L[zA]
    resA_R = resA_R[zA]

    # Branch B poles:
    poleB = muMid + 1j * np.pi * kT * (2 * dummyindex + 1)  # Analytical pole location from definition of fermi-fun
    # Residues for left
    resB_L = -(2j * np.pi * kT) * fermi_fun(poleB, 1j * muIm, 1j * kTIm)
    # Residues for right are exactly the negatives of the left by design
    resB_R = -resB_L
    # Determine which to trim
    zB = (np.abs(resB_L) >= np.exp(-p) * kT) & (np.imag(poleB) > 0)
    poleB = poleB[zB]
    resB_L = resB_L[zB]
    resB_R = resB_R[zB]

    # Branch C poles:
    poleC = muMax + 1j * np.pi * kT * (2 * dummyindex + 1)  # Analytical pole location from definition of fermi-fun
    # Residues for left
    resC_L = 0 * poleC
    # Residues for right
    resC_R = -(2j * np.pi * kT) * fermi_fun(poleC, 1j * muIm, 1j * kTIm)
    # Determine which to trim
    zC = (np.abs(resC_R) >= np.exp(-p) * kT) & (np.imag(poleC) > 0)
    poleC = poleC[zC]
    resC_L = resC_L[zC]
    resC_R = resC_R[zC]

    # Branch D poles:
    poleD = 1j * muIm - np.pi * kTIm * (2 * dummyindex + 1)  # Analytical pole location from definition of fermi-fun
    # Residues for left
    resD_L = (2 * np.pi * kTIm) * (fermi_fun(poleD, muMid, kT) - fermi_fun(poleD, muMin, kT))
    # Residues for right
    resD_R = (2 * np.pi * kTIm) * (fermi_fun(poleD, muMax, kT) - fermi_fun(poleD, muMid, kT))
    # Determine which to trim

    zD = np.maximum(np.abs(resD_L), np.abs(resD_R)) > np.exp(-p) * kT
    poleD = poleD[zD]
    resD_L = resD_L[zD]
    resD_R = resD_R[zD]

    poles = np.concatenate((poleA, poleB, poleC, poleD))
    residuesL = np.concatenate((resA_L, resB_L, resC_L, resD_L))
    residuesR = np.concatenate((resA_R, resB_R, resC_R, resD_R))

    return poles, residuesL, residuesR


def fermi_fun(E, mu, kT):
    """
    Computes the Fermi-Dirac distribution function. Auxiliary function just to tidy the workspace.

    Parameters
    ----------
    E    : scalar (dtype=numpy.float)
         Energy being evaluated
    mu   : scalar (dtype=numpy.float)
         Chemical potential
    kT   : scalar (dtype=numpy.float)
         Temperature (in units of energy)
    """
    # Tanh should be more numerically stable than 1/(exp(x) + 1), however
    # numpy has issues with large complex values in both exp and tanh
    # x = (E - mu)/kT
    # return 1/(np.exp(x) + 1)

    x = (E - mu) / (2 * kT)
    return 0.5 * (1 - np.tanh(x))


def fermi_deriv(E, mu, kT):
    """
    Computes the Fermi-Dirac distribution function derivative. Auxiliary function just to tidy the workspace.

    Parameters
    ----------
    E    : scalar (dtype=numpy.float)
         Energy being evaluated
    mu   : scalar (dtype=numpy.float)
         Chemical potential
    kT   : scalar (dtype=numpy.float)
         Temperature (in units of energy)
    """
    # Tanh should be more numerically stable than 1/(exp(x) + 1), however
    # numpy has issues with large complex values in both exp and tanh
    # x = (E - mu)/kT
    # return 1/(np.exp(x) + 1)

    x = (E - mu) / (2 * kT)
    return (np.cosh(x) ** -2) / (4 * kT)


def fermi_deriv2(E, mu, kT):
    """
    Computes the Fermi-Dirac distribution function second derivative. Auxiliary function just to tidy the workspace.

    Parameters
    ----------
    E    : scalar (dtype=numpy.float)
         Energy being evaluated
    mu   : scalar (dtype=numpy.float)
         Chemical potential
    kT   : scalar (dtype=numpy.float)
         Temperature (in units of energy)
    """
    # Tanh should be more numerically stable than 1/(exp(x) + 1), however
    # numpy has issues with large complex values in both exp and tanh
    # x = (E - mu)/kT
    # return 1/(np.exp(x) + 1)

    x = (E - mu) / (2 * kT)
    return np.tanh(x) * (np.cosh(x) ** -2) / (4 * kT ** 2)