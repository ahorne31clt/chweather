"""Headless broadcast-style map. No pyplot GUI backend or external font service."""
from pathlib import Path
import textwrap

import matplotlib
matplotlib.use('Agg', force=True)
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Rectangle
import matplotlib.patheffects as pe
import cartopy.crs as ccrs
import numpy as np
from PIL import Image
from .model import haversine

BG='#18191A'; WHITE='#E8EBE8'; SAGE='#9FB4AC'; GREEN='#0B6B45'; GOLD='#C19244'
COLORS=['#303b38','#3d765b','#8cad7d','#c19244','#df976c']
LABELS=['Limited','Fair','Good','Very good','Excellent']


def render(path, root, latitudes, longitudes, score, mask, usa, countries, states, metadata):
    plt.rcParams.update({'font.family':'DejaVu Sans','text.color':WHITE,'font.size':10})
    fig=plt.figure(figsize=(16,10),dpi=150,facecolor=BG)
    try:
        logo=fig.add_axes([.012,.885,.076,.105]); logo.axis('off')
        logo.imshow(Image.open(Path(root)/'assets/ch-weather-logo.png'))
        fig.text(.102,.941,'SUNSET OUTLOOK',fontsize=27,weight='bold')
        fig.text(.103,.909,'CONUS  /  EVENING COLOR POTENTIAL',fontsize=10,color=GOLD,weight='bold')
        fig.text(.985,.951,metadata['forecast_valid_date'],ha='right',fontsize=13,weight='bold')
        fig.text(.985,.925,'VALID AT EACH LOCATION’S SUNSET',ha='right',fontsize=8.5,color=SAGE)
        fig.text(.985,.903,'EXPERIMENTAL  /  NOT A PROBABILITY',ha='right',fontsize=8.5,color=GOLD)
        fig.add_artist(plt.Line2D([.014,.986],[.884,.884],color=GREEN,lw=1.5,transform=fig.transFigure))
        projection=ccrs.LambertConformal(central_longitude=-96,central_latitude=38,standard_parallels=(33,45))
        ax=fig.add_axes([.012,.135,.758,.733],projection=projection)
        ax.set_facecolor('#121817')
        ax.set_extent([-125, -66, 24, 50],crs=ccrs.PlateCarree())
        ax.add_geometries(countries,ccrs.PlateCarree(),facecolor='#222827',edgecolor='#52615a',linewidth=.45,zorder=1)
        lon,lat=np.meshgrid(longitudes,latitudes)
        values=np.ma.masked_where(~mask,score)
        cmap=ListedColormap(COLORS)
        ax.contourf(lon,lat,values,levels=[0,20,40,60,80,100.001],cmap=cmap,
                    norm=BoundaryNorm([0,20,40,60,80,100.001],5),transform=ccrs.PlateCarree(),
                    corner_mask=False,zorder=2,antialiased=False)
        ax.add_geometries([usa],ccrs.PlateCarree(),facecolor='none',edgecolor='#a8b5ab',linewidth=.65,zorder=4)
        ax.add_geometries(states,ccrs.PlateCarree(),facecolor='none',edgecolor='#a0b2a677',linewidth=.4,zorder=4)
        # Context labels kept quiet; the national maxima are numbered separately.
        for name,x,y in [('Seattle',-122.33,47.61),('Los Angeles',-118.24,34.05),('Denver',-104.99,39.74),
                         ('Dallas',-96.8,32.78),('Chicago',-87.63,41.88),('Charlotte',-80.84,35.23),
                         ('New York',-74.01,40.71),('Miami',-80.19,25.76)]:
            color=GOLD if name=='Charlotte' else WHITE
            near_pick=min(float(haversine(y,x,p['latitude'],p['longitude'])) for p in metadata['top_locations']) < 220
            if near_pick and name!='Charlotte':
                continue
            ax.plot(x,y,'.',ms=2.5,color=color,transform=ccrs.PlateCarree(),zorder=5)
            dx,dy=(-3,-.7) if near_pick else (.38,.12)
            label=ax.text(x+dx,y+dy,name,color=color,fontsize=7.2,transform=ccrs.PlateCarree(),zorder=5)
            label.set_path_effects([pe.withStroke(linewidth=2,foreground=BG)])
        for place in metadata['top_locations']:
            x,y=place['longitude'],place['latitude']
            ax.plot(x,y,'o',ms=18,markeredgecolor=WHITE,markeredgewidth=1.2,color=GREEN,
                    transform=ccrs.PlateCarree(),zorder=8)
            ax.text(x,y,str(place['rank']),ha='center',va='center',fontsize=9,weight='bold',
                    transform=ccrs.PlateCarree(),zorder=9)
        ax.spines['geo'].set_edgecolor('#52615a')
        fig.text(.025,.84,'LOCAL SUNSET TIME • 0.25° MODEL INPUT',fontsize=8,color=WHITE,
                 bbox=dict(facecolor=BG,edgecolor='none',pad=7))
        sidebar=fig.add_axes([.79,.135,.195,.733]); sidebar.set_facecolor(BG); sidebar.set_xlim(0,1);sidebar.set_ylim(0,1);sidebar.axis('off')
        sidebar.text(0,.97,'COLOR POTENTIAL',weight='bold',fontsize=12)
        sidebar.text(0,.93,'Relative index / 0–100',color=SAGE,fontsize=9)
        for i,(color,label) in enumerate(zip(COLORS,LABELS)):
            y=.87-i*.049
            sidebar.add_patch(Rectangle((0,y-.008),.07,.027,facecolor=color))
            sidebar.text(.11,y,f'{i*20:02d}–{(i+1)*20:02d}  {label}',va='center',fontsize=9)
        sidebar.axhline(.625,color='#52615a',lw=.6)
        sidebar.text(0,.59,'TOP 3 / SPREAD OUT',fontsize=11,weight='bold',color=GOLD)
        sidebar.text(0,.555,'At least 600 km apart · relative picks',fontsize=8,color=SAGE)
        for i,place in enumerate(metadata['top_locations']):
            y=.50-i*.129
            sidebar.text(0,y,f"0{place['rank']}  /  {place['score']:.0f}",weight='bold',fontsize=14)
            sidebar.text(0,y-.035,place['label'],fontsize=9,weight='bold')
            sidebar.text(0,y-.064,f"{place['latitude']:.2f}°N, {abs(place['longitude']):.2f}°W",fontsize=8,color=SAGE)
            sidebar.text(0,y-.088,f"{place['nearest_city_distance_km']} km from named city",fontsize=7.5,color=SAGE)
        sidebar.text(0,.057,'Good locations are relative to today.\nEven the top picks may have low potential.',fontsize=8,color=SAGE,linespacing=1.6)
        fig.add_artist(plt.Line2D([.014,.986],[.112,.112],color=GOLD,lw=.8,transform=fig.transFigure))
        fig.text(.02,.083,'CH WEATHER',weight='bold',fontsize=12)
        fig.text(.16,.083,'Cloud placement can change. An open western horizon helps.',fontsize=10)
        fig.text(.02,.054,f"NOAA/NCEP GFS 0.25° · Run {metadata['model_run']} · Natural Earth boundaries",fontsize=8,color=SAGE)
        fig.text(.02,.029,f"Generated {metadata['generated_at_utc']}  |  Student meteorologist Christopher Horne  |  @chornewx",fontsize=8,color=SAGE)
        fig.text(.985,.029,'Experimental guidance, not an NWS/SPC product.',ha='right',fontsize=8,color=GOLD)
        fig.savefig(path,dpi=150,facecolor=BG,metadata={'Title':'CH Weather experimental sunset outlook'})
    finally:
        plt.close(fig)
    with Image.open(path) as image:
        if image.size != (2400,1500):
            raise ValueError('Unexpected graphic dimensions')
        image.verify()
