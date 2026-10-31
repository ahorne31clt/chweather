import matplotlib
matplotlib.use('Agg',force=True)
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm
import cartopy.crs as ccrs
import numpy as np
import gzip,hashlib
from PIL import Image
from models.render import projection_for,native_axes
from sunset.render import BG,WHITE,SAGE,GOLD,GREEN

COLORS=['#25332f','#315842','#47835b','#76a66b','#a5b979','#c5b569','#c49a53','#cf7f52','#bd5e64','#985d86']
PRODUCTS={
 'gefs':{'freeze':('2 m temperature <32°F','Pointwise probability; strictly below freezing at the valid time.'),
         'hot90':('2 m temperature >90°F','Pointwise probability; strictly above 90°F at the valid time.'),
         'rain01':('6-hour precipitation ≥0.10 in','Pointwise probability of at least 0.10 inch liquid-equivalent precipitation in the preceding six hours.'),
         'rain05':('6-hour precipitation ≥0.50 in','Pointwise probability of at least 0.50 inch liquid-equivalent precipitation in the preceding six hours.'),
         'rain1':('6-hour precipitation ≥1.00 in','Pointwise probability of at least 1.00 inch liquid-equivalent precipitation in the preceding six hours.')},
 'refs':{'freeze':('2 m temperature <32°F','NOAA published point probability of temperature below freezing.'),
         'cape1000':('Mixed-layer CAPE >1000 J/kg','NOAA published probability for CAPE in the lowest 90-mb mixed layer. Not a severe-storm probability.'),
         'rain1':('6-hour precipitation >1.00 in','NOAA published NEIGHBORHOOD probability of more than 1 inch liquid-equivalent precipitation in six hours. This is not a point rain chance. The publisher’s neighborhood processing is retained unchanged.')}
}


def render(path,root,model,run,hour,product,values,grid,metadata,geo):
    title,description=PRODUCTS[model][product];source=projection_for(grid) if grid['type']=='lambert' else ccrs.PlateCarree()
    proj=source if grid['type']=='lambert' else ccrs.LambertConformal(central_longitude=-96,central_latitude=38,standard_parallels=(33,45))
    from datetime import timedelta
    valid=run+timedelta(hours=hour);start=valid-timedelta(hours=6) if product.startswith('rain') else valid
    fig=plt.figure(figsize=(16,9),dpi=125,facecolor=BG);plt.rcParams.update({'font.family':'DejaVu Sans','text.color':WHITE})
    try:
        logo=fig.add_axes([.01,.91,.055,.08]);logo.axis('off');logo.imshow(Image.open(root/'assets/ch-weather-logo.png'))
        fig.text(.076,.957,model.upper()+' / '+title.upper(),fontsize=18,weight='bold')
        kind='NEIGHBORHOOD' if model=='refs' and product=='rain1' else 'POINTWISE'
        fig.text(.077,.926,f'ENSEMBLE PROBABILITY % · {metadata["member_count"]} MEMBERS · {kind}',fontsize=9,color=GOLD)
        fig.text(.987,.964,f'F{hour:03d} · '+valid.strftime('%d %b %Y %H UTC'),ha='right',fontsize=10,weight='bold')
        fig.text(.987,.934,'RUN '+run.strftime('%d %b %H UTC'),ha='right',fontsize=8,color=SAGE)
        ax=fig.add_axes([.012,.125,.976,.775],projection=proj);ax.set_extent([-125,-66,24,50],ccrs.PlateCarree());ax.set_facecolor('#1c2821')
        cmap=ListedColormap(COLORS);norm=BoundaryNorm(list(range(0,101,10)),10)
        if grid['type']=='lambert':
            x,y=native_axes(grid,proj)
            image=ax.imshow(values,origin='lower' if grid['j_positive'] else 'upper',extent=[min(x)-grid['dx']/2,max(x)+grid['dx']/2,min(y)-grid['dy']/2,max(y)+grid['dy']/2],transform=proj,cmap=cmap,norm=norm,interpolation='nearest')
        else:
            xx,yy=np.meshgrid(grid['longitudes'],grid['latitudes']);image=ax.pcolormesh(xx,yy,values,transform=source,cmap=cmap,norm=norm,shading='nearest',rasterized=True)
        ax.add_geometries(geo[1],ccrs.PlateCarree(),facecolor='none',edgecolor='#111713',linewidth=.9,zorder=4)
        ax.add_geometries(geo[2],ccrs.PlateCarree(),facecolor='none',edgecolor='#111713',linewidth=.65,zorder=4)
        ax.spines['geo'].set_edgecolor('#657a68')
        color=fig.add_axes([.24,.075,.57,.018]);bar=fig.colorbar(image,cax=color,orientation='horizontal',ticks=list(range(0,101,10)));bar.ax.tick_params(labelsize=8,colors=WHITE);bar.outline.set_edgecolor('#647a68')
        fig.text(.015,.075,'CH WEATHER',fontsize=11,weight='bold');fig.text(.83,.076,'PROBABILITY %',fontsize=8,color=SAGE)
        window=start.strftime('%d %b %H UTC')+' – '+valid.strftime('%d %b %H UTC') if product.startswith('rain') else valid.strftime('%d %b %H UTC (instantaneous)')
        fig.text(.015,.031,'VALID '+window+' · NOAA/NCEP · Natural Earth · Christopher Horne / @chornewx',fontsize=8,color=SAGE)
        fig.savefig(path,dpi=125,facecolor=BG)
        # Small, nearest-native numerical lookup for cursor/tap readouts. Its
        # 5-image-pixel spacing is display sampling, not added model resolution.
        from scipy.interpolate import RegularGridInterpolator
        px,py=np.meshgrid(np.arange(400)*5+2.5,np.arange(225)*5+2.5)
        display=np.column_stack((px.ravel(),1125-py.ravel()))
        native=ax.transData.inverted().transform(display)
        converted=source.transform_points(proj,native[:,0],native[:,1])
        axes=(y,x) if grid['type']=='lambert' else (grid['latitudes'],grid['longitudes'])
        sampled=RegularGridInterpolator(axes,values,method='nearest',bounds_error=False,fill_value=np.nan)(np.column_stack((converted[:,1],converted[:,0])))
        bounds=ax.get_window_extent();inside=(display[:,0]>=bounds.x0)&(display[:,0]<=bounds.x1)&(display[:,1]>=bounds.y0)&(display[:,1]<=bounds.y1)&np.isfinite(sampled)
        encoded=np.full(sampled.shape,65535,dtype='<u2');encoded[inside]=np.rint(sampled[inside]*10).astype('<u2')
        target=path.with_suffix('.bin.gz');target.write_bytes(gzip.compress(encoded.tobytes(),mtime=0))
        return dict(filename=target.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),width=400,height=225,scale=10,missing=65535)
    finally:plt.close(fig)
