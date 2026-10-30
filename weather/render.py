"""Shared sharp-edged CH Weather graphic system; headless Matplotlib only."""
from pathlib import Path
import textwrap

import matplotlib
matplotlib.use('Agg',force=True)
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, PathPatch
from matplotlib.path import Path as MplPath
from matplotlib.colors import ListedColormap, BoundaryNorm
import matplotlib.patheffects as effects
import cartopy.crs as ccrs
from cartopy.mpl.patch import geos_to_path
import numpy as np
from PIL import Image

from sunset.render import BG,WHITE,SAGE,GREEN,GOLD
from .sources import SPC_CATEGORIES

REGIONS={'national':[-125,-66,24,50],'nc':[-84.6,-75,33.5,37.3]}
FOLIAGE_LABELS=['Little / no color','Low color','Moderate color','High color','Peak color','Past peak']
FOLIAGE_COLORS=['#689C4B','#F6ED5F','#FFA228','#D45C17','#A30F10','#4D2B0F']
TEMP_LEVELS=[-20,0,20,32,40,50,60,70,80,90,100,120]
TEMP_COLORS=['#615a91','#657f9d','#6a9da6','#91bcb5','#7da886','#6f9b58','#a6ae63','#c5a353','#d08b51','#cb6f52','#a85655']


def render(path,root,product,geo,lat=None,lon=None,values=None,records=None,raster=None):
    plt.rcParams.update({'font.family':'DejaVu Sans','text.color':WHITE,'font.size':10})
    fig=plt.figure(figsize=(16,10),dpi=150,facecolor=BG)
    try:
        logo=fig.add_axes([.012,.885,.076,.105]);logo.axis('off')
        logo.imshow(Image.open(root/'assets/ch-weather-logo.png'))
        fig.text(.103,.942,product['title'],fontsize=24,weight='bold')
        fig.text(.104,.911,product['subtitle'],fontsize=9.5,color=GOLD,weight='bold')
        date=product.get('source_date',product.get('valid_start_utc','')[:10])
        fig.text(.985,.95,date,ha='right',fontsize=13,weight='bold')
        fig.text(.985,.924,product['source'],ha='right',fontsize=8,color=SAGE)
        fig.text(.985,.903,'CH WEATHER PRESENTATION',ha='right',fontsize=8,color=GOLD)
        fig.add_artist(plt.Line2D([.014,.986],[.883,.883],color=GREEN,lw=1.5,transform=fig.transFigure))
        region=product['region']
        proj=ccrs.LambertConformal(central_longitude=-79.8 if region=='nc' else -96,
            central_latitude=35.5 if region=='nc' else 38,standard_parallels=(33,45))
        ax=fig.add_axes([.012,.15,.758,.716],projection=proj)
        ax.set_extent(REGIONS[region],crs=ccrs.PlateCarree());ax.set_facecolor('#121817')
        ax.add_geometries(geo['countries'],ccrs.PlateCarree(),facecolor='#222827',edgecolor='#58665f',linewidth=.45,zorder=1)
        if values is not None:
            xx,yy=np.meshgrid(lon,lat)
            if product['type']=='rain':
                levels=[0,10,20,30,40,50,60,70,80,90,100.01]
                colors=['#273a33','#315842','#3f7550','#5d925c','#87ac70','#b7bc7a','#c5ad60','#c59650','#bc7c48','#a96042']
            else: levels,colors=TEMP_LEVELS,TEMP_COLORS
            contours=ax.contourf(xx,yy,np.ma.masked_invalid(values),levels=levels,
                cmap=ListedColormap(colors),norm=BoundaryNorm(levels,len(colors)),
                transform=ccrs.PlateCarree(),corner_mask=False,antialiased=False,zorder=2,extend='both')
            geometry=geo['nc' if region=='nc' else 'usa']
            outline_path=MplPath.make_compound_path(*geos_to_path(geometry))
            contours.set_clip_path(PathPatch(outline_path,transform=ccrs.PlateCarree()._as_mpl_transform(ax)))
        if raster is not None:
            merc=ccrs.GOOGLE_MERCATOR
            west,south=merc.transform_point(-126,23,ccrs.PlateCarree())
            east,north=merc.transform_point(-65,52,ccrs.PlateCarree())
            with Image.open(raster) as image:
                # Preserve publisher colors, categories, and source resolution.
                ax.imshow(np.array(image.convert('RGBA')),origin='upper',extent=[west,east,south,north],
                    transform=merc,interpolation='nearest',regrid_shape=1000,zorder=2)
        if records is not None:
            order=list(SPC_CATEGORIES)
            for label,geometry in sorted(records,key=lambda item:order.index(item[0])):
                ax.add_geometries([geometry],ccrs.PlateCarree(),facecolor=SPC_CATEGORIES[label][1],
                    edgecolor='#17251a',linewidth=.9,alpha=.88,zorder=3+order.index(label)*.1)
        ax.add_geometries(geo['states'],ccrs.PlateCarree(),facecolor='none',edgecolor='#b0beb17d',linewidth=.55,zorder=5)
        ax.add_geometries([geo['usa']],ccrs.PlateCarree(),facecolor='none',edgecolor=SAGE,linewidth=.65,zorder=6)
        if region=='nc': ax.add_geometries([geo['nc']],ccrs.PlateCarree(),facecolor='none',edgecolor=GOLD,linewidth=1.2,zorder=7)
        for city in product.get('cities',[]):
            x,y=city['lon'],city['lat'];name=city['name']
            label=name
            if product['type']=='weather' and city.get('high_f') is not None:
                label+=f"\n{city['high_f']:.0f}°"
                if city.get('pop_percent') is not None:label+=f" / {city['pop_percent']:.0f}%"
            elif product['type']=='rain' and city.get('pop_percent') is not None: label+=f"\n{city['pop_percent']:.0f}%"
            color=GOLD if name=='Charlotte' else WHITE
            ax.plot(x,y,'.',ms=3,color=color,transform=ccrs.PlateCarree(),zorder=8)
            text=ax.text(x+(.12 if region=='nc' else .4),y+.08,label,color=color,
                         fontsize=8.5 if region=='nc' else 7.2,transform=ccrs.PlateCarree(),zorder=9)
            text.set_path_effects([effects.withStroke(linewidth=2.3,foreground=BG)])
        ax.spines['geo'].set_edgecolor('#52615a')
        side=fig.add_axes([.791,.15,.194,.716]);side.axis('off');side.set_xlim(0,1);side.set_ylim(0,1)
        kind=product['type']
        if kind=='spc':
            side.text(0,.97,'SPC CATEGORY KEY',fontsize=12,weight='bold')
            active={r[0] for r in records}
            for i,(code,(label,color)) in enumerate(SPC_CATEGORIES.items()):
                y=.89-i*.065
                side.add_patch(Rectangle((0,y-.012),.07,.031,facecolor=color))
                side.text(.11,y,f'{code} / {label}',va='center',fontsize=9,
                          color=WHITE if code in active else SAGE)
            highest=max(active,key=lambda key:list(SPC_CATEGORIES).index(key)) if active else None
            risk='No risk areas outlined.' if highest is None else ('General thunderstorms only.' if highest=='TSTM' else f'Highest severe category: {SPC_CATEGORIES[highest][0]}.')
            side.text(0,.43,'THIS ISSUANCE',fontsize=10,color=GOLD,weight='bold')
            side.text(0,.39,'\n'.join(textwrap.wrap(risk,34)),fontsize=9,color=WHITE)
            side.text(0,.29,'\n'.join(textwrap.wrap(product['summary'],39)[:10]),fontsize=8,color=SAGE,va='top',linespacing=1.45)
        elif kind=='foliage':
            side.text(0,.97,'EXPLORE FALL ESTIMATE',fontsize=11,weight='bold')
            for i,(label,color) in enumerate(zip(FOLIAGE_LABELS,FOLIAGE_COLORS)):
                y=.88-i*.06;side.add_patch(Rectangle((0,y-.01),.07,.03,facecolor=color))
                side.text(.11,y,label,va='center',fontsize=9)
            side.text(0,.43,'PUBLISHED MODEL LAYER',color=GOLD,fontsize=10,weight='bold')
            side.text(0,.38,'Not a direct observation.\nColor varies by slope and species.\nNo location peak date is inferred.',fontsize=9,color=SAGE,linespacing=1.7,va='top')
            side.text(0,.19,'ExploreFall.com\nFull interactive map and reports\navailable from the source.',fontsize=9,color=SAGE,linespacing=1.7)
        elif kind=='rain':
            side.text(0,.97,'PRECIPITATION CHANCE',fontsize=11,weight='bold')
            for i in range(10):
                y=.9-i*.042;side.add_patch(Rectangle((0,y-.008),.07,.025,facecolor=colors[i]))
                side.text(.11,y,f'{i*10}–{(i+1)*10}%',va='center',fontsize=9)
            side.text(0,.41,'ONE 12-HOUR INTERVAL',color=GOLD,fontsize=10,weight='bold')
            side.text(0,.36,'Chance of measurable precipitation\n(0.01 in / 0.254 mm), including\nrain or frozen precipitation.\nNot percent of the day it rains.\nNot a 24-hour probability.',fontsize=8.5,color=SAGE,linespacing=1.7,va='top')
        else:
            side.text(0,.97,'DAYTIME HIGH / °F',fontsize=12,weight='bold')
            for i,color in enumerate(TEMP_COLORS):
                y=.89-i*.04;side.add_patch(Rectangle((0,y-.008),.07,.025,facecolor=color))
                side.text(.11,y,f'{TEMP_LEVELS[i]}–{TEMP_LEVELS[i+1]}°',va='center',fontsize=9)
            side.text(0,.39,'CITY LABELS',color=GOLD,fontsize=10,weight='bold')
            side.text(0,.34,'High temperature / precipitation %\nSame 12-hour forecast interval.\nNWS grids, presented by CH Weather.\nNot a separately hand-edited forecast.',fontsize=8.5,color=SAGE,linespacing=1.7,va='top')
        if kind!='foliage':
            side.text(0,.105,'VALID UTC',fontsize=8,color=GOLD,weight='bold')
            start=product['valid_start_utc'].replace('T',' ')[:16];end=product['valid_end_utc'].replace('T',' ')[:16]
            side.text(0,.075,f'{start}\nto {end}',fontsize=8,color=SAGE,linespacing=1.6,va='top')
        fig.add_artist(plt.Line2D([.014,.986],[.119,.119],color=GOLD,lw=.8,transform=fig.transFigure))
        fig.text(.02,.09,'CH WEATHER',fontsize=12,weight='bold')
        foot='Explore Fall model estimate · Source date '+product['source_date'] if kind=='foliage' else f"Issued {product['issued_at_utc']} · Valid {product['valid_start_utc']} to {product['valid_end_utc']}"
        fig.text(.16,.09,foot,fontsize=8.5)
        fig.text(.02,.058,product['source']+' · Natural Earth boundaries · '+product['kind'],fontsize=8,color=SAGE)
        fig.text(.02,.031,'Generated '+product['generated_at_utc']+' | Student meteorologist Christopher Horne | @chornewx',fontsize=8,color=SAGE)
        fig.savefig(path,dpi=150,facecolor=BG)
    finally:plt.close(fig)
    with Image.open(path) as image:
        if image.size!=(2400,1500):raise ValueError('Incorrect graphic size')
        image.verify()
