import textwrap
import matplotlib
matplotlib.use('Agg',force=True)
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm
from matplotlib.path import Path
from matplotlib.transforms import Affine2D
import matplotlib.patheffects as effects
from matplotlib.patches import PathPatch
from cartopy.mpl.patch import geos_to_path
import cartopy.crs as ccrs
from shapely.geometry import LineString
import numpy as np
from PIL import Image
from .config import PRODUCTS
from weather.render import REGIONS
from sunset.render import BG,WHITE,SAGE,GREEN,GOLD


def draw_fronts(ax,projection,data,regional):
    colors={'COLD':'#59a6e4','WARM':'#ef7775','STNRY':'#59a6e4','OCFNT':'#bb8bd0','TROF':'#d2ad64'}
    triangle=Path([[-.6,0],[.6,0],[0,.9],[-.6,0]])
    arc=Path.wedge(0,180)
    for kind in colors:
        for line in data[kind]:
            xy=projection.transform_points(ccrs.PlateCarree(),np.array(line)[:,1],np.array(line)[:,0])[:,:2]
            if len(xy)<2 or not np.isfinite(xy).all():continue
            ax.plot(xy[:,0],xy[:,1],color=colors[kind],lw=1.8,ls='--' if kind=='TROF' else '-',transform=projection,zorder=10,path_effects=[effects.withStroke(linewidth=3.5,foreground=BG)])
            if kind=='TROF':continue
            curve=LineString(xy);spacing=65000 if regional else 220000
            for number,d in enumerate(np.arange(spacing/2,curve.length,spacing)):
                a=curve.interpolate(max(0,d-1000));b=curve.interpolate(min(curve.length,d+1000));point=curve.interpolate(d)
                angle=np.degrees(np.arctan2(b.y-a.y,b.x-a.x));color=colors[kind]
                marker=triangle if kind=='COLD' or kind in ('STNRY','OCFNT') and number%2==0 else arc
                if kind=='STNRY' and number%2:angle+=180;color=colors['WARM']
                ax.scatter([point.x],[point.y],marker=marker.transformed(Affine2D().rotate_deg(angle)),s=52,color=color,edgecolors='none',transform=projection,zorder=11,clip_on=True)
    for name,letter,color in [('LOWS','L','#f28c83'),('HIGHS','H','#8fc3e7')]:
        for lat,lon in data[name]:
            ax.text(lon,lat,letter,fontsize=19,weight='bold',ha='center',va='center',color=color,transform=ccrs.PlateCarree(),clip_on=True,zorder=12,path_effects=[effects.withStroke(linewidth=3,foreground=BG)])


def render(path,root,kind,region,lat,lon,values,geo,meta,front=None,rain=None):
    spec=PRODUCTS[kind];regional=region=='nc'
    plt.rcParams.update({'font.family':'DejaVu Sans','text.color':WHITE,'font.size':10})
    fig=plt.figure(figsize=(16,10),dpi=150,facecolor=BG)
    try:
        logo=fig.add_axes([.012,.887,.078,.103]);logo.imshow(Image.open(root/'assets/ch-weather-logo.png'));logo.axis('off')
        fig.text(.105,.951,spec['title'],weight='bold',fontsize=23)
        fig.text(.106,.92,('NORTH CAROLINA' if regional else 'CONUS')+' / '+spec['kind'].upper(),fontsize=9,color=GOLD)
        fig.text(.985,.95,'UNDERSTAND WHAT’S AHEAD.',ha='right',fontsize=9,weight='bold',color=SAGE)
        fig.text(.985,.923,'NOAA / NCEP NBM',ha='right',fontsize=9,color=GOLD)
        fig.add_artist(plt.Line2D([.012,.988],[.889,.889],color=GREEN,lw=1.7,transform=fig.transFigure))
        proj=ccrs.LambertConformal(central_longitude=-79.8 if regional else -96,central_latitude=35.5 if regional else 38,standard_parallels=(33,45))
        ax=fig.add_axes([.012,.175,.976,.695],projection=proj);ax.set_extent(REGIONS[region],ccrs.PlateCarree());ax.set_facecolor('#111a17')
        ax.add_geometries(geo['countries'],ccrs.PlateCarree(),facecolor='#232b26',edgecolor='#59675e',lw=.5,zorder=0)
        xx,yy=np.meshgrid(lon,lat)
        contours=ax.contourf(xx,yy,np.ma.masked_invalid(values),levels=spec['levels'],cmap=ListedColormap(spec['colors']),norm=BoundaryNorm(spec['levels'],len(spec['colors'])),transform=ccrs.PlateCarree(),corner_mask=False,antialiased=False,extend='both',zorder=2)
        mask=geo['nc' if regional else 'usa'];clip=Path.make_compound_path(*geos_to_path(mask));contours.set_clip_path(PathPatch(clip,transform=ccrs.PlateCarree()._as_mpl_transform(ax)))
        if rain is not None and np.nanmax(rain)>=50:
            rain_layer=ax.contourf(xx,yy,np.ma.masked_invalid(rain),levels=[50,100.1],colors='none',hatches=['////'],transform=ccrs.PlateCarree(),zorder=3)
            rain_layer.set_clip_path(PathPatch(clip,transform=ccrs.PlateCarree()._as_mpl_transform(ax)))
        ax.add_geometries(geo['states'],ccrs.PlateCarree(),facecolor='none',edgecolor='#0a1510',lw=.65,zorder=4)
        ax.add_geometries([mask],ccrs.PlateCarree(),facecolor='none',edgecolor='#9cafa2',lw=.7,zorder=5)
        if front:draw_fronts(ax,proj,front,regional)
        cities=[('Charlotte',35.23,-80.84),('Raleigh',35.78,-78.64),('Asheville',35.60,-82.55),('Wilmington',34.23,-77.94)] if regional else [('Seattle',47.61,-122.33),('Los Angeles',34.05,-118.24),('Denver',39.74,-104.99),('Dallas',32.78,-96.80),('Chicago',41.88,-87.63),('Charlotte',35.23,-80.84),('New York',40.71,-74.01)]
        for name,a,b in cities:
            row=int(np.argmin(abs(lat-a)));col=int(np.argmin(abs(lon-b)));value=values[row,col]
            readout='' if not np.isfinite(value) else (f' {value:.2f}' if kind=='ice' else f' {value:.1f}' if kind in ('snow','confidence') else f' {value:.0f}')
            if kind=='frost':readout=''
            ax.plot(b,a,'.',ms=3,color=WHITE,transform=ccrs.PlateCarree(),zorder=15)
            ax.text(b+(.08 if regional else .3),a+.06,name+readout,fontsize=8,transform=ccrs.PlateCarree(),zorder=15,path_effects=[effects.withStroke(linewidth=2.7,foreground=BG)])
        cax=fig.add_axes([.025,.137,.55,.012]);bar=fig.colorbar(contours,cax=cax,orientation='horizontal',ticks=spec['levels'][1:-1]);bar.ax.tick_params(labelsize=7,colors=WHITE);bar.outline.set_edgecolor('#4d6153')
        fig.text(.59,.139,spec['unit'].upper(),fontsize=8,color=GOLD,weight='bold')
        if kind=='frost':fig.text(.025,.104,'0 NO SIGNAL / 1 FROST-FAVORABLE / 2 FREEZE ≤32°F / 3 HARD-FREEZE ≤28°F',fontsize=8)
        elif front:fig.text(.025,.104,'WPC FRONTS / HATCH: ≥50% PRECIP CHANCE IN AT LEAST ONE 6H PERIOD (NOT 24H PoP)',fontsize=7.8)
        else:fig.text(.025,.104,' / '.join(textwrap.wrap(spec['description'],110)[:2]),fontsize=8,color=SAGE)
        fig.text(.985,.139,('VALID '+meta['valid_start_utc']+' → '+meta['valid_end_utc']).replace('T',' ').replace(':00Z','Z'),ha='right',fontsize=8)
        if kind=='confidence':detail='SPREAD VALID '+meta['confidence_valid_at_utc']
        elif front:detail='WPC FRONTS VALID '+meta['fronts']['valid_at_utc']
        elif kind=='stargazing':detail=f'MOON ILLUMINATION {meta["moon"]["illuminated_percent"]:.0f}% / SHOWN SEPARATELY, NOT IN INDEX'
        else:detail='NBM RUN '+meta['model_run']
        fig.text(.985,.104,detail,ha='right',fontsize=8,color=GOLD)
        fig.add_artist(plt.Line2D([.012,.988],[.088,.088],color=GREEN,lw=1,transform=fig.transFigure))
        fig.text(.02,.063,'CH WEATHER',weight='bold',fontsize=11)
        fig.text(.15,.063,'NBM guidance / Experimental indices are not calibrated probabilities or official warnings.',fontsize=8,color=SAGE)
        fig.text(.02,.033,'RUN '+meta['model_run']+' / GENERATED '+meta['generated_at_utc']+' / Original WPC boundaries where shown / Natural Earth',fontsize=7.5,color=SAGE)
        fig.text(.985,.033,'Christopher Horne / Student meteorologist',ha='right',fontsize=7.5,color=GOLD)
        fig.savefig(path,facecolor=BG)
    finally:plt.close(fig)
