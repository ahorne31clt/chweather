import matplotlib
matplotlib.use('Agg',force=True)
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap,BoundaryNorm
import cartopy.crs as ccrs
import numpy as np
from PIL import Image

from models.render import projection_for,native_axes
from models.fields import PRODUCTS
from sunset.render import BG,WHITE,SAGE,GOLD,GREEN
from .data import humidity

REGIONS={'conus':('CONUS',[-125,-66,24,50]),'carolinas':('CAROLINAS',[-85.5,-74,31,37.8])}
FIELDS={'temperature':('2 M TEMPERATURE','°F','temp2m'),'dewpoint':('2 M DEWPOINT','°F','dewpoint2m'),
        'humidity':('DERIVED 2 M RELATIVE HUMIDITY','%','rh2m'),'wind':('10 M SUSTAINED WIND','kt','wind10'),
        'gust':('10 M WIND GUST','kt','wind10'),'stations':('SURFACE OBSERVATIONS','',None)}


def render(path,root,run,fields,grid,geo,region,field,stations):
    projection=projection_for(grid);x,y=native_axes(grid,projection)
    fig=plt.figure(figsize=(16,9),dpi=150,facecolor=BG)
    plt.rcParams.update({'font.family':'DejaVu Sans','text.color':WHITE})
    try:
        logo=fig.add_axes([.008,.909,.055,.08]);logo.axis('off');logo.imshow(Image.open(root/'assets/ch-weather-logo.png'))
        title,unit,config=FIELDS[field]
        fig.text(.075,.952,'RTMA / '+title,fontsize=20,weight='bold')
        fig.text(.076,.919,REGIONS[region][0]+' · NOAA/NCEP 2.5 KM ANALYSIS · STATION OVERLAY: METAR OBSERVATIONS',fontsize=8,color=GOLD)
        fig.text(.985,.955,run.strftime('VALID %d %b %Y / %H:%M UTC'),ha='right',fontsize=10,weight='bold')
        fig.text(.985,.925,'ANALYSIS, NOT A FORECAST',ha='right',fontsize=8,color=SAGE)
        ax=fig.add_axes([.012,.12,.976,.775],projection=projection);ax.set_extent(REGIONS[region][1],ccrs.PlateCarree());ax.set_facecolor('#1c2821')
        ax.add_geometries(geo[1],ccrs.PlateCarree(),facecolor='#222d26',edgecolor='#9caf9f',linewidth=.5)
        if config:
            spec=PRODUCTS[config];values=humidity(fields['temperature'],fields['dewpoint']) if field=='humidity' else fields[field]
            if field in ('temperature','dewpoint'):values=(values-273.15)*1.8+32
            elif field in ('wind','gust'):values=values*1.94384449
            cmap=LinearSegmentedColormap.from_list(field,spec['colors']);norm=BoundaryNorm(spec['levels'],256,extend='both')
            plot=ax.imshow(values,origin='lower' if grid['j_positive'] else 'upper',extent=[min(x)-grid['dx']/2,max(x)+grid['dx']/2,min(y)-grid['dy']/2,max(y)+grid['dy']/2],transform=projection,cmap=cmap,norm=norm,interpolation='nearest',zorder=2)
            colorax=fig.add_axes([.26,.065,.58,.016]);bar=fig.colorbar(plot,cax=colorax,orientation='horizontal',extend='both');bar.ax.tick_params(labelsize=7,colors=WHITE);bar.outline.set_edgecolor('#6c7e70')
            fig.text(.87,.068,unit,color=WHITE,fontsize=9,weight='bold')
        else:fig.text(.26,.068,'METAR: TEMPERATURE / DEWPOINT °F · WIND kt · SLP LAST THREE DIGITS (hPa × 10)',fontsize=8,color=SAGE)
        ax.add_geometries(geo[1],ccrs.PlateCarree(),facecolor='none',edgecolor='#111813',linewidth=.9,zorder=4)
        ax.add_geometries(geo[2],ccrs.PlateCarree(),facecolor='none',edgecolor='#111813' if config else '#7f9685',linewidth=.65,zorder=4)
        ax.spines['geo'].set_edgecolor('#597160')
        fig.text(.016,.068,'CH WEATHER',weight='bold',fontsize=11)
        fig.text(.016,.03,'NOAA/NCEP RTMA · NOAA/AWC METAR · Natural Earth boundaries · Christopher Horne / @chornewx',fontsize=8,color=SAGE)
        fig.canvas.draw()
        # Convert observation locations to image pixels; vector rotation keeps
        # true-direction station wind barbs aligned with this map projection.
        positions={}
        for station in stations:
            lon,lat=station['longitude'],station['latitude']
            west,east,south,north=REGIONS[region][1]
            if not west<=lon<=east or not south<=lat<=north:continue
            px,py=projection.transform_point(lon,lat,ccrs.PlateCarree());sx,sy=ax.transData.transform((px,py))
            box=ax.get_window_extent()
            if not box.x0+45<sx<box.x1-45 or not box.y0+50<sy<box.y1-50:continue
            direction=station['wind_direction'];speed=station['wind_kt']
            vector=None
            if direction is not None and speed is not None and speed>0:
                a=np.deg2rad(direction);u,v=-speed*np.sin(a),-speed*np.cos(a)
                uu,vv=projection.transform_vectors(ccrs.PlateCarree(),np.array([lon]),np.array([lat]),np.array([u]),np.array([v]))
                length=float(np.hypot(uu[0],vv[0]));vector=[float(-uu[0]/length),float(vv[0]/length)]
            positions[station['id']]=dict(x=round(float(sx),2),y=round(float(1350-sy),2),wind_from_vector=vector)
        bounds=ax.get_window_extent()
        mapbox=[bounds.x0,1350-bounds.y1,bounds.width,bounds.height]
        fig.savefig(path,dpi=150,facecolor=BG)
        return dict(positions=positions,map_box=[round(float(v),2) for v in mapbox])
    finally:plt.close(fig)
