"""Branded headless seasonal maps; retain native coarse-grid context."""
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


def render(path,root,lat,lon,values,geo,meta,stations=None,support=None):
    plt.rcParams.update({'font.family':'DejaVu Sans','text.color':WHITE,'font.size':10})
    fig=plt.figure(figsize=(16,9.2),dpi=125,facecolor=BG)
    try:
        logo=fig.add_axes([.013,.894,.065,.094]);logo.imshow(Image.open(root/'assets/ch-weather-logo.png'));logo.axis('off')
        fig.text(.09,.958,meta['title'].upper(),fontsize=20,weight='bold')
        fig.text(.091,.923,meta['model_label'].upper()+' / '+meta['season_label'].upper(),fontsize=10,color=GOLD)
        fig.text(.985,.962,'CH WEATHER',ha='right',weight='bold',fontsize=13)
        fig.text(.985,.930,'INITIALIZED '+meta['initialization_month'],ha='right',fontsize=9,color=SAGE)
        fig.add_artist(plt.Line2D([.013,.987],[.893,.893],transform=fig.transFigure,color=GREEN,lw=2))
        ax=fig.add_axes([.013,.145,.974,.731],projection=ccrs.LambertConformal(central_longitude=-96,central_latitude=38,standard_parallels=(33,45)))
        ax.set_extent([-125,-66,24,50],ccrs.PlateCarree());ax.set_facecolor('#111915')
        usa,countries,states=geo
        ax.add_geometries(countries,ccrs.PlateCarree(),facecolor='#263029',edgecolor='#58665c',lw=.6,zorder=0)
        if meta['metric'] in ('amount','total'):
            from .blend import SNOW_BANDS,SNOW_LABELS
            levels=SNOW_BANDS
            colors=['#c8d1c8','#6a8e78','#91b6a6','#b5d4d0','#94c1d5','#6fa1cc','#8c88bb','#ac7fac','#c38fba','#e6c4da']
        elif meta['metric']!='anomaly':
            levels=[0,20,30,33.34,40,50,60,70,80,90,100.01]
            colors=['#aeb7af','#939f94','#7d907c','#698864','#558353','#4e9255','#6dac64','#91c47b','#bade98','#e1efc2']
        elif meta['variable']=='temperature':
            levels=[-10,-6,-4,-2,-1,1,2,4,6,10]
            colors=['#234e80','#387aae','#6eabc9','#a3ccd8','#dee3db','#e4d2a0','#d68d51','#ba563a','#8c302a']
        else:
            levels=([-12,-8,-4,-2,-1,-.25,.25,1,2,4,8,12] if meta['variable']=='snowfall' else [-6,-4,-2,-1,-.5,-.1,.1,.5,1,2,4,6])
            colors=['#70432e','#9b6238','#bb8951','#d2ad79','#e0ceb0','#dee3db','#c4ddc2','#9bc79b','#6da87a','#3f825c','#14563f']
        xx,yy=np.meshgrid(lon,lat)
        if np.isfinite(values).sum()<8:raise ValueError('Insufficient map values to render')
        extension='max' if meta['metric'] in ('amount','total') else 'both' if meta['metric']=='anomaly' else 'neither'
        artist=ax.contourf(xx,yy,np.ma.masked_invalid(values),levels=levels,cmap=ListedColormap(colors),norm=BoundaryNorm(levels,len(colors)),
                           transform=ccrs.PlateCarree(),extend=extension,corner_mask=False,zorder=2,antialiased=False)
        clip=Path.make_compound_path(*geos_to_path(usa))
        artist.set_clip_path(PathPatch(clip,transform=ccrs.PlateCarree()._as_mpl_transform(ax)))
        ax.add_geometries(states,ccrs.PlateCarree(),facecolor='none',edgecolor='#101812',lw=.75,zorder=5)
        ax.add_geometries([usa],ccrs.PlateCarree(),facecolor='none',edgecolor='#98afa1',lw=.7,zorder=6)
        cb=fig.colorbar(artist,cax=fig.add_axes([.19,.105,.62,.018]),orientation='horizontal',extend=extension)
        if meta['metric']=='amount':
            cb.set_ticks([(a+b)/2 for a,b in zip(levels,levels[1:])]);cb.set_ticklabels(SNOW_LABELS)
        cb.ax.tick_params(labelsize=8,colors=WHITE);cb.set_label(meta['units_label'],fontsize=9,color=WHITE)
        fig.text(.018,.047,meta['footer'],fontsize=8,color=SAGE)
        fig.text(.018,.023,'Student meteorologist Christopher Horne / @chornewx / Natural Earth boundaries',fontsize=8,color=SAGE)
        fig.text(.984,.023,'EXPERIMENTAL SEASONAL GUIDANCE',fontsize=8,color=GOLD,ha='right')
        fig.savefig(path,dpi=125,facecolor=BG)
        # Compact palette PNGs preserve contour readability and keep Pages small.
        with Image.open(path) as original:
            compact=original.convert('RGB').quantize(colors=256,dither=Image.Dither.NONE)
        compact.save(path,format='PNG',optimize=True,compress_level=9)
    finally:plt.close(fig)
