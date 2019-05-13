"""
Forward modelling for point masses
"""
import numpy as np
from numba import jit

from ..constants import GRAVITATIONAL_CONST


def point_mass_gravity(coordinates, point, mass, field, dtype="float64"):
    """
    Compute gravitational fields of a point mass on spherical coordinates.

    Parameters
    ----------
    coordinates : list or array
        List or array containing `longitude`, `latitude` and `radius` of computation
        points defined on a spherical geocentric coordinate system.
        Both `longitude` and `latitude` should be in degrees and `radius` in meters.
    point : list or array
        Coordinates of the point mass: [`longitude`, `latitude`, `radius`] defined on
        a spherical geocentric coordinate system.
        Both `longitude` and `latitude` should be in degrees and `radius` in meters.
    mass : float
        Mass of the point mass in kg.
    field : str
        Gravitational field that wants to be computed.
        The available fields are:

        - Gravitational potential: ``potential``
        - Radial acceleration: ``g_radial``

    Returns
    -------
    gravitational_field : array
        Gravitational field generated by the `point_mass` on the computation points
        defined in `coordinates`.
        The potential is given in SI units, the accelerations in mGal and the Marussi
        tensor components in Eotvos.
    """
    kernels = {"potential": kernel_potential, "g_radial": kernel_g_radial}
    if field not in kernels:
        raise ValueError("Gravity field {} not recognized".format(field))
    # Figure out the shape and size of the output array
    cast = np.broadcast(*coordinates[:3])
    result = np.zeros(cast.size, dtype=dtype)
    longitude, latitude, radius = (i.ravel() for i in coordinates[:3])
    jit_point_mass_gravity(longitude, latitude, radius, point, kernels[field], result)
    result *= GRAVITATIONAL_CONST * mass
    # Convert to more convenient units
    if field in ("g_radial"):
        result *= 1e5  # SI to mGal
    return result.reshape(cast.shape)


@jit(nopython=True)
def jit_point_masses_gravity(
    coordinates, longitude_p, latitude_p, radius_p, masses, kernel
):
    """
    Compute gravity field of point masses on a single computation point
    """
    # Compute quantities related to computation point
    longitude, latitude, radius = coordinates[:]
    longitude = np.radians(longitude)
    latitude = np.radians(latitude)
    cosphi = np.cos(latitude)
    sinphi = np.sin(latitude)
    # Compute quantities related to point masses
    longitude_p = np.radians(longitude_p)
    latitude_p = np.radians(latitude_p)
    cosphi_p = np.cos(latitude_p)
    sinphi_p = np.sin(latitude_p)
    radius_p_sq = radius_p ** 2
    # Compute gravity field
    out = 0
    for l in range(longitude_p.size):
        out += masses[l] * kernel(
            longitude,
            cosphi,
            sinphi,
            radius,
            longitude_p[l],
            cosphi_p[l],
            sinphi_p[l],
            radius_p[l],
            radius_p_sq[l],
        )
    return out


@jit(nopython=True)
def jit_point_mass_gravity(longitude, latitude, radius, point, kernel, out):
    """
    """
    longitude_p, latitude_p, radius_p = point[:]
    longitude_p, latitude_p = np.radians(longitude_p), np.radians(latitude_p)
    cosphi_p = np.cos(latitude_p)
    sinphi_p = np.sin(latitude_p)
    radius_p_sq = radius_p ** 2
    cosphi = np.cos(np.radians(latitude))
    sinphi = np.sin(np.radians(latitude))
    longitude_radians = np.radians(longitude)
    for l in range(out.size):
        out[l] += kernel(
            longitude_radians[l],
            cosphi[l],
            sinphi[l],
            radius[l],
            longitude_p,
            cosphi_p,
            sinphi_p,
            radius_p,
            radius_p_sq,
        )


@jit(nopython=True)
def kernel_potential(
    longitude,
    cosphi,
    sinphi,
    radius,
    longitude_p,
    cosphi_p,
    sinphi_p,
    radius_p,
    radius_p_sq,
):
    coslambda = np.cos(longitude_p - longitude)
    cospsi = sinphi_p * sinphi + cosphi_p * cosphi * coslambda
    distance_sq = radius ** 2 + radius_p_sq - 2 * radius * radius_p * cospsi
    return 1 / np.sqrt(distance_sq)


@jit(nopython=True)
def kernel_g_radial(
    longitude,
    cosphi,
    sinphi,
    radius,
    longitude_p,
    cosphi_p,
    sinphi_p,
    radius_p,
    radius_p_sq,
):
    coslambda = np.cos(longitude_p - longitude)
    cospsi = sinphi_p * sinphi + cosphi_p * cosphi * coslambda
    distance_sq = radius ** 2 + radius_p_sq - 2 * radius * radius_p * cospsi
    delta_z = radius_p * cospsi - radius
    return delta_z / distance_sq ** (3 / 2)
