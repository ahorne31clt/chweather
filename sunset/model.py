"""Transparent heuristics, not a trained or calibrated probability model."""
import calendar
from datetime import datetime, timezone

import numpy as np
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage import gaussian_filter

MODEL_VERSION = 'ch-sunset-2.0.0'
MIN_SEPARATION_KM = 600


def solar_sunset(day, lat, lon):
    """NOAA approximate equations; UTC hours from midnight of local calendar date.

    Hours can exceed 24 (western US sunset on the next UTC date). Flat horizon,
    standard refraction; these are not terrain-corrected event times.
    """
    lat, lon = np.broadcast_arrays(np.asarray(lat, float), np.asarray(lon, float))
    phi = np.deg2rad(lat)
    utc_hour = 18 - lon / 15
    doy = day.timetuple().tm_yday
    for _ in range(3):
        gamma = 2 * np.pi / (366 if calendar.isleap(day.year) else 365) * (doy - 1 + (utc_hour - 12) / 24)
        eq = 229.18 * (.000075 + .001868*np.cos(gamma) - .032077*np.sin(gamma)
                       - .014615*np.cos(2*gamma) - .040849*np.sin(2*gamma))
        dec = (.006918 - .399912*np.cos(gamma) + .070257*np.sin(gamma)
               - .006758*np.cos(2*gamma) + .000907*np.sin(2*gamma)
               - .002697*np.cos(3*gamma) + .00148*np.sin(3*gamma))
        cos_ha = np.cos(np.deg2rad(90.833))/(np.cos(phi)*np.cos(dec)) - np.tan(phi)*np.tan(dec)
        if np.any(np.abs(cos_ha) > 1):
            raise ValueError('No sunset at one or more grid points')
        ha = np.rad2deg(np.arccos(cos_ha))
        utc_hour = (720 - 4*lon - eq + 4*ha) / 60
    altitude = np.deg2rad(-.833)
    azimuth = 360 - np.rad2deg(np.arccos(np.clip(
        (np.sin(dec)-np.sin(phi)*np.sin(altitude))/(np.cos(phi)*np.cos(altitude)), -1, 1)))
    return utc_hour, azimuth


def destination(lat, lon, bearing, km):
    phi, lam, angle = map(np.deg2rad, (lat, lon, bearing))
    distance = km / 6371.0088
    new_phi = np.arcsin(np.sin(phi)*np.cos(distance)+np.cos(phi)*np.sin(distance)*np.cos(angle))
    new_lam = lam + np.arctan2(np.sin(angle)*np.sin(distance)*np.cos(phi),
                              np.cos(distance)-np.sin(phi)*np.sin(new_phi))
    return np.rad2deg(new_phi), np.rad2deg(new_lam)


def haversine(lat, lon, other_lat, other_lon):
    phi1, phi2 = np.deg2rad(lat), np.deg2rad(other_lat)
    delta_phi = phi2 - phi1
    delta_lam = np.deg2rad(other_lon) - np.deg2rad(lon)
    a = np.sin(delta_phi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(delta_lam/2)**2
    return 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def quality_score(low, middle, high, horizon_blocker, visibility):
    """All clouds are fractions, visibility meters. Exact weights in docs."""
    # Broken rather than completely overcast cloud fields are preferred.
    upper = np.maximum(.9*high, .7*middle)
    canvas = np.clip(upper/.55, 0, 1) * (1-.45*np.clip((upper-.65)/.35, 0, 1))
    score = (18+82*canvas) * (1-.9*low)**1.3
    score *= (1-.85*horizon_blocker)**1.2
    score *= .75 + .25*np.clip(visibility/16000, 0, 1)
    return np.clip(score, 0, 100)


def calculate(day, latitudes, longitudes, valid_hours, fields):
    target_lat = latitudes[(latitudes >= 24) & (latitudes <= 50)]
    target_lon = longitudes[(longitudes >= -125) & (longitudes <= -66)]
    lon, lat = np.meshgrid(target_lon, target_lat)
    hours, azimuth = solar_sunset(day, lat, lon)
    if hours.min() < valid_hours[0] or hours.max() > valid_hours[-1]:
        raise ValueError('Forecast times do not bracket every grid point sunset')
    points = np.column_stack([hours.ravel(), lat.ravel(), lon.ravel()])
    interpolators = {
        key: RegularGridInterpolator((valid_hours, latitudes, longitudes), cube, bounds_error=True)
        for key, cube in fields.items()
    }
    sampled = {key: fun(points).reshape(lat.shape) for key, fun in interpolators.items()}
    blockers = []
    # Sample cloud obstruction toward the actual seasonal solar azimuth, at
    # the OBSERVER's sunset time, not the horizon location's sunset time.
    for distance in (80, 160, 240):
        hlat, hlon = destination(lat, lon, azimuth, distance)
        # Edge padding is downloaded; report a failure rather than extrapolate.
        hpoints = np.column_stack([hours.ravel(), hlat.ravel(), hlon.ravel()])
        low = interpolators['low'](hpoints).reshape(lat.shape)
        mid = interpolators['middle'](hpoints).reshape(lat.shape)
        blockers.append(np.maximum(low, .6*mid))
    horizon = np.mean(blockers, axis=0)
    raw = quality_score(sampled['low'], sampled['middle'], sampled['high'], horizon, sampled['visibility'])
    # Only smooth for ~one native grid cell; never claim added physical resolution.
    score = gaussian_filter(raw, sigma=.65, mode='nearest')
    return score, hours, sampled


def top_locations(score, latitudes, longitudes, mask, cities, sunset_hours, day, count=3):
    if np.ndim(latitudes) == 2:
        lat, lon = latitudes, longitudes
    else:
        lon, lat = np.meshgrid(longitudes, latitudes)
    candidates = np.where(mask, score, -np.inf).copy()
    selected = []
    midnight = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    for rank in range(1, count+1):
        row, col = np.unravel_index(np.argmax(candidates), candidates.shape)
        if not np.isfinite(candidates[row, col]):
            raise ValueError('Insufficient separated land locations')
        y, x = float(lat[row,col]), float(lon[row,col])
        distances = [float(haversine(y,x,c['lat'],c['lon'])) for c in cities]
        closest = cities[int(np.argmin(distances))]
        from datetime import timedelta
        selected.append(dict(rank=rank, latitude=y, longitude=x, score=round(float(score[row,col]),1),
                             label=f"Near {closest['name']}", nearest_city_distance_km=round(min(distances)),
                             sunset_utc=(midnight+timedelta(hours=float(sunset_hours[row,col]))).isoformat().replace('+00:00','Z')))
        candidates[haversine(y,x,lat,lon) < MIN_SEPARATION_KM] = -np.inf
    return selected
