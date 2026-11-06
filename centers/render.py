"""CH Weather cartography drawn from official forecast vectors."""
import matplotlib
matplotlib.use('Agg',force=True)
import matplotlib.pyplot as plt
from matplotlib.patches import Patch,PathPatch
from matplotlib.path import Path
from matplotlib.colors import to_rgb,to_hex
from cartopy.mpl.patch import geos_to_path
import cartopy.crs as ccrs
from PIL import Image
from sunset.render import BG,WHITE,SAGE,GREEN,GOLD

ERO={'Marginal':'#73a774','Slight':'#d5bd60','Moderate':'#d18d55','High':'#bb5752'}
QPF_LEVELS=[.01,.1,.25,.5,1,1.5,2,2.5,3,4,5,7,10,15,20]
QPF_COLORS=['#dce4d8','#bdd5c0','#94bfac','#6aa991','#468b74','#26745c','#12583e','#77934e','#aab156','#c8af57','#b38e51','#a37575','#925c9c','#724980','#4e345c']


def color(item,row):
    group=item['group'];v=row['value'];cat=row['category']
    if group=='ero':return ERO[cat]
    if group=='qpf':return QPF_COLORS[max(i for i,t in enumerate(QPF_LEVELS) if v>=t)]
    if group=='tropical':return {'Low':'#d0b653','Medium':'#d58b51','High':'#c75b55'}[cat]
    if cat in ('EC','Normal'):return '#c9d1c7' if cat=='EC' else '#a5b2a7'
    base=('#b94e35' if cat=='Above' else '#386c9b') if group=='temperature' else ('#22734d' if cat=='Above' else '#a1743e')
    strength=max(.25,min(1,(v-25)/75));neutral=to_rgb('#e2e5d9');rgb=to_rgb(base)
    return to_hex(tuple(a+(b-a)*strength for a,b in zip(neutral,rgb)))


def render(path,root,item,rows,geo,*,extent=None,points=None,note=None):
    plt.rcParams.update({'font.family':'DejaVu Sans','text.color':WHITE})
    tropical=item['group']=='tropical';domain=extent or [-125,-66,24,50]
    projection=ccrs.PlateCarree() if tropical else ccrs.LambertConformal(central_longitude=-96,central_latitude=38,standard_parallels=(33,45))
    fig=plt.figure(figsize=(16,10),dpi=125,facecolor=BG)
    try:
        logo=fig.add_axes([.013,.89,.065,.09]);logo.imshow(Image.open(root/'assets/ch-weather-logo.png'));logo.axis('off')
        fig.text(.09,.955,item['title'].upper(),fontsize=22,weight='bold')
        fig.text(.09,.922,'CH WEATHER / OFFICIAL '+item['center'].upper()+' GUIDANCE / '+item.get('domain','CONUS').upper(),fontsize=9,color=GOLD)
        issued=item.get('published_at_utc') or item.get('issued_at_utc') or item.get('issued_date') or 'See source bulletin'
        fig.text(.985,.96,('BULLETIN PUBLISHED ' if item.get('published_at_utc') else 'ISSUED ')+issued.replace('T',' ')[:20],ha='right',fontsize=8,color=SAGE)
        fig.text(.985,.897,'VALID '+item['valid_period_label'],ha='right',fontsize=9,color=WHITE)
        fig.add_artist(plt.Line2D([.013,.987],[.883,.883],transform=fig.transFigure,color=GREEN,lw=2))
        ax=fig.add_axes([.013,.17,.974,.69],projection=projection);ax.set_extent(domain,ccrs.PlateCarree());ax.set_facecolor('#101b19')
        usa,countries,states=geo
        ax.add_geometries(countries,ccrs.PlateCarree(),facecolor='#303b33' if tropical else '#b8c2b6',edgecolor='#748579',lw=.5,zorder=0)
        clip=Path.make_compound_path(*geos_to_path(usa))
        # Broad outer contours first, then stronger nested contours. No new interpolation.
        for row in sorted(rows,key=lambda r:(r['category'] not in ('EC','Normal'),r['value'])):
            artist=ax.add_geometries([row['geometry']],ccrs.PlateCarree(),facecolor=color(item,row),edgecolor=color(item,row) if not tropical else WHITE,lw=.35 if not tropical else 1.2,zorder=2,alpha=.72 if tropical else 1)
            if not tropical:artist.set_clip_path(PathPatch(clip,transform=ccrs.PlateCarree()._as_mpl_transform(ax)))
        ax.add_geometries(states,ccrs.PlateCarree(),facecolor='none',edgecolor='#111d16' if not tropical else '#687b6c',lw=.65,zorder=4)
        if not tropical:ax.add_geometries([usa],ccrs.PlateCarree(),facecolor='none',edgecolor='#294233',lw=.7,zorder=5)
        if tropical:
            ax.gridlines(draw_labels={'bottom':'x','left':'y'},linewidth=.35,color=SAGE,alpha=.3,x_inline=False,y_inline=False)
            for point in points or []:
                x,y=point['geometry'].x,point['geometry'].y
                if not domain[0]<=x<=domain[1] or not domain[2]<=y<=domain[3]:continue
                ax.plot(x,y,marker='x',ms=9,mew=2,color=color(item,point),transform=ccrs.PlateCarree(),zorder=8)
                ax.text(x+1,y+1,str(point.get('label',''))+' / '+str(int(point['value']))+'%',color=WHITE,fontsize=10,weight='bold',transform=ccrs.PlateCarree(),zorder=9)
            if note:ax.text(.5,.055,note,transform=ax.transAxes,color=WHITE,fontsize=11,ha='center',bbox=dict(facecolor=BG,edgecolor=GREEN,pad=12),zorder=10)
        elif item.get('empty_forecast_statement'):
            ax.text(.5,.08,item['empty_forecast_statement'],transform=ax.transAxes,color=WHITE,fontsize=12,ha='center',bbox=dict(facecolor=BG,edgecolor=GREEN,pad=12),zorder=10)
        if item['group']=='qpf':
            handles=[Patch(facecolor=c,label=str(t)) for t,c in zip(QPF_LEVELS,QPF_COLORS)]
            legend=fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.09),ncol=len(handles),frameon=False,fontsize=7,handlelength=1,columnspacing=.8)
            label='WPC liquid-equivalent accumulation contours / inches'
        elif item['group']=='ero':
            handles=[Patch(facecolor=c,label=f'{name} / at least {p}%') for (name,c),p in zip(ERO.items(),[5,15,40,70])]
            legend=fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.09),ncol=4,frameon=False,fontsize=9);label='Rainfall exceeding flash-flood guidance within 25 miles of a point / not a warning'
        elif tropical:
            handles=[Patch(facecolor=c,label=l) for c,l in [('#d0b653','Low / below 40%'),('#d58b51','Medium / 40-60%'),('#c75b55','High / above 60%')]]
            legend=fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.09),ncol=3,frameon=False,fontsize=9);label='Development probability during the stated period / areas are formation regions, not forecast tracks'
        else:
            handles=[Patch(facecolor=color(item,dict(category=cat,value=p)),label=f'{cat} {int(p)}%') for cat in ('Below','Above') for p in (33,40,50,60,70,80,90)]
            handles+=[Patch(facecolor='#c9d1c7',label='Equal chances')]
            normal=sorted({r['value'] for r in rows if r['category']=='Normal'})
            handles+=[Patch(facecolor='#a5b2a7',label='Near normal'+('/'.join(str(int(n)) for n in normal)+'%' if normal else ''))]
            legend=fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.083),ncol=8,frameon=False,fontsize=7,columnspacing=1)
            label='Official category probability contours / not anomaly magnitude / shaded near-normal areas retained'
        for text in legend.get_texts():text.set_color(WHITE)
        fig.text(.5,.065,label,fontsize=8,color=WHITE,ha='center')
        fig.text(.02,.036,'Forecast areas, probabilities and valid periods: NOAA / NWS / '+item['center'].upper()+'. Cartography: CH Weather. Not a separate CH Weather forecast.',fontsize=8,color=SAGE)
        fig.text(.02,.016,'Christopher Horne / Student meteorologist / Natural Earth boundaries / '+item.get('domain','CONUS'),fontsize=8,color=SAGE)
        fig.savefig(path,facecolor=BG)
        with Image.open(path) as image:image.convert('RGB').quantize(colors=256).save(path,optimize=True)
    finally:plt.close(fig)
