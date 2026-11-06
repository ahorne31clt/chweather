"""Model capabilities shared by generation and artifact publication."""
MODELS={
 'gfs':dict(name='GFS',end=384,step=3,resolution='0.25 degrees',airports=True,credit='NOAA/NCEP'),
 'hrrr':dict(name='HRRR',end=48,step=1,resolution='3 km',airports=True,credit='NOAA/NCEP'),
 'rrfs':dict(name='RRFS',end=84,step=3,resolution='3 km',airports=False,credit='NOAA/NCEP'),
 'ecmwf':dict(name='ECMWF IFS / Euro',end=360,step=3,resolution='0.25 degrees',airports=False,credit='ECMWF Open Data / CC BY 4.0'),
 'woofnam':dict(name='WOOF-NAM',end=84,step=3,resolution='12.19 km',airports=False,credit='WOOF-NAM by Recast / CC BY 4.0'),
}
