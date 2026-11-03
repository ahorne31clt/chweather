"""Branded contour-filled solar-optics ingredient maps."""
import matplotlib
matplotlib.use('Agg',force=True)
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm
from matplotlib.path import Path
from matplotlib.patches import PathPatch
from cartopy.mpl.patch import geos_to_path
import cartopy.crs as ccrs
from PIL import Image
import numpy as np
from sunset.render import BG,WHITE,SAGE,GREEN,GOLD
from .science import PHENOMENA


def render(path,root,key,region,lat,lon,values,geo,meta):
    plt.rcParams.update({'font.family':'DejaVu Sans','text.color':WHITE})
    fig=plt.figure(figsize=(16,9.2),dpi=125,facecolor=BG)
    try:
        logo=fig.add_axes([.013,.894,.065,.094]);logo.imshow(Image.open(root/'assets/ch-weather-logo.png'));logo.axis('off')
        fig.text(.09,.958,PHENOMENA[key][0].upper()+('' if key=='contrail' else ' / INGREDIENT FAVORABILITY'),fontsize=18,weight='bold')
        fig.text(.091,.923,('NORTH CAROLINA' if region=='nc' else 'CONUS')+' / EXPERIMENTAL SOLAR OPTICS',fontsize=10,color=GOLD)
        fig.text(.985,.960,'CH WEATHER',ha='right',weight='bold',fontsize=13)
        fig.text(.985,.932,('GFS TEMPERATURE / SPECIFIC HUMIDITY' if key=='contrail' else 'HRRR CLOUDS / GFS PROFILES' if meta.get('hrrr',{}).get('status')=='available' else 'GFS')+' / '+meta['model_run'][:16].replace('T',' ')+'Z',ha='right',fontsize=8,color=SAGE)
        fig.add_artist(plt.Line2D([.013,.987],[.893,.893],transform=fig.transFigure,color=GREEN,lw=2))
        regional=region=='nc';projection=ccrs.LambertConformal(central_longitude=-80 if regional else -96,central_latitude=35 if regional else 38)
        ax=fig.add_axes([.013,.18,.974,.69],projection=projection)
        ax.set_extent([-84.6,-75,33.5,37.3] if regional else [-125,-66,24,50],ccrs.PlateCarree());ax.set_facecolor('#111915')
        usa,countries,states=geo
        ax.add_geometries(countries,ccrs.PlateCarree(),facecolor='#263029',edgecolor='#58665c',lw=.6,zorder=0)
        levels=[0,10,25,45,65,100.01];colors=['#283b33','#426c51','#5c9364','#9ebd72','#d3b16a']
        if key=='contrail':levels=[-.5,.5,1.5,2.5];colors=['#283b33','#b49d62','#66a77f']
        xx,yy=np.meshgrid(lon,lat)
        artist=ax.contourf(xx,yy,np.ma.masked_invalid(values),levels=levels,cmap=ListedColormap(colors),norm=BoundaryNorm(levels,len(colors)),transform=ccrs.PlateCarree(),antialiased=False,zorder=2)
        clip=Path.make_compound_path(*geos_to_path(usa));artist.set_clip_path(PathPatch(clip,transform=ccrs.PlateCarree()._as_mpl_transform(ax)))
        ax.add_geometries(states,ccrs.PlateCarree(),facecolor='none',edgecolor='#080f0c',lw=.8,zorder=5)
        ax.add_geometries([usa],ccrs.PlateCarree(),facecolor='none',edgecolor='#9fb4ac',lw=.6,zorder=6)
        fig.text(.02,.147,('HIGHEST HOURLY ENVIRONMENT CATEGORY' if key=='contrail' else 'BEST HOURLY INGREDIENT SCORE')+' / '+meta['valid_start_utc'][:16].replace('T',' ')+'Z TO '+meta['valid_end_utc'][:16].replace('T',' ')+'Z',color=SAGE,fontsize=9)
        bar=fig.colorbar(artist,cax=fig.add_axes([.18,.104,.64,.018]),orientation='horizontal',ticks=[0,1,2] if key=='contrail' else [0,10,25,45,65,100]);bar.ax.tick_params(colors=WHITE,labelsize=8)
        if key=='contrail':bar.ax.set_xticklabels(['No qualifying sampled layer','Formation only','Persistence environment'])
        fig.text(.5,.069,'Conditional on an aircraft crossing the layer / not flight, halo or sundog odds' if key=='contrail' else 'Heuristic ingredient index / not a probability / best times vary by location',ha='center',fontsize=9)
        fig.text(.02,.035,'Ice-crystal shape/orientation and optical depth are unresolved. No display is guaranteed. Never look directly at the Sun.',fontsize=8,color=SAGE)
        fig.text(.02,.014,'NOAA/NCEP / '+('GFS upper-air contrail environment' if key=='contrail' else meta['model'])+' / 0.25 degree scoring grid / CH Weather research guidance',fontsize=8,color=SAGE)
        fig.savefig(path,facecolor=BG)
        with Image.open(path) as image:image.convert('RGB').quantize(colors=256).save(path,optimize=True)
    finally:plt.close(fig)
