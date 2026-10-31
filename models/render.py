from pathlib import Path
from datetime import timedelta

import matplotlib
matplotlib.use('Agg',force=True)
import matplotlib.pyplot as plt
import matplotlib.patheffects as effects
from matplotlib.patches import Rectangle
from matplotlib.colors import LinearSegmentedColormap,BoundaryNorm
from matplotlib.cm import ScalarMappable
import cartopy.crs as ccrs
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.interpolate import RegularGridInterpolator
from PIL import Image
from shapely.geometry import Point
from shapely.prepared import prep

from sunset.render import BG,WHITE,SAGE,GREEN,GOLD
from .product import classify,diagnostics,pressure_centers,TYPE_COLORS,TYPE_NAMES
from .fields import PRODUCTS,scalar_field


def projection_for(grid):
    if grid['type']=='lambert':
        globe=ccrs.Globe(ellipse=None,semimajor_axis=grid['earth_radius'],semiminor_axis=grid['earth_radius'])
        return ccrs.LambertConformal(central_longitude=grid['central_lon'],central_latitude=grid['central_lat'],
            standard_parallels=(grid['parallel1'],grid['parallel2']),globe=globe)
    return ccrs.LambertConformal(central_longitude=-96,central_latitude=38,standard_parallels=(33,45))


def native_axes(grid,projection):
    x0,y0=projection.transform_point(grid['first_lon'],grid['first_lat'],ccrs.PlateCarree())
    x=x0+np.arange(grid['cols'])*grid['dx']*(-1 if grid['i_negative'] else 1)
    y=y0+np.arange(grid['rows'])*grid['dy']*(1 if grid['j_positive'] else -1)
    return x,y


def draw_pressure_centers(ax,pressure,x,y,source_crs,projection):
    # Analyze both models on the same ~35 km projected grid, so HRRR's
    # denser native grid does not produce a forest of tiny pressure labels.
    xmin,xmax=ax.get_xlim();ymin,ymax=ax.get_ylim()
    gx=np.arange(xmin,xmax,35000);gy=np.arange(ymin,ymax,35000)
    xx,yy=np.meshgrid(gx,gy)
    coordinates=source_crs.transform_points(projection,xx,yy)
    interpolator=RegularGridInterpolator((y,x),pressure,bounds_error=False,fill_value=np.nan)
    sampled=interpolator(np.stack([coordinates[:,:,1],coordinates[:,:,0]],axis=-1))
    for kind,row,col,value in pressure_centers(sampled):
        px,py=gx[col],gy[row]
        # Keep symbols and numeric labels comfortably inside the map frame.
        if not (.035<(px-xmin)/(xmax-xmin)<.965 and .055<(py-ymin)/(ymax-ymin)<.945):continue
        color='#72B6DD' if kind=='H' else '#F17878'
        symbol=ax.text(px,py,kind,ha='center',va='center',fontsize=23,weight='bold',
                       color=color,transform=projection,zorder=10,clip_on=True)
        symbol.set_path_effects([effects.withStroke(linewidth=3.5,foreground=BG)])
        ax.annotate(f'{value:.0f}',xy=(px,py),xycoords=projection._as_mpl_transform(ax),
                    xytext=(0,-18),textcoords='offset points',ha='center',va='center',
                    fontsize=7.5,weight='bold',color=WHITE,zorder=10,clip_on=True,
                    bbox=dict(boxstyle='square,pad=.15',facecolor=BG,edgecolor='none',alpha=.9))


def grid_sample(values,x,y,source_crs,projection,xx,yy):
    points=source_crs.transform_points(projection,np.asarray(xx),np.asarray(yy))
    return RegularGridInterpolator((y,x),values,method='nearest',bounds_error=False,fill_value=np.nan)(np.stack([points[...,1],points[...,0]],axis=-1))


def write_readouts(path,ax,fields,x,y,source_crs,projection):
    from .readouts import write_grid
    return write_grid(path,ax,fields,x,y,source_crs,projection,grid_sample)


def draw_wind_barbs(ax,grid,x,y,fields,projection,source_crs,level='500'):
    stride=max(1,round(165000/grid['dx'])) if grid['type']=='lambert' else 7
    xx,yy=np.meshgrid(x[::stride],y[::stride])
    u=fields['u'+level][::stride,::stride]*1.94384449244
    v=fields['v'+level][::stride,::stride]*1.94384449244
    mask=~np.isfinite(u)|~np.isfinite(v)|(np.hypot(u,v)<5)
    vector_crs=source_crs
    if grid['type']=='lambert' and not grid.get('wind_grid_relative',1):
        coords=ccrs.PlateCarree().transform_points(projection,xx,yy)
        xx,yy=coords[...,0],coords[...,1];vector_crs=ccrs.PlateCarree()
    barbs=ax.barbs(xx,yy,np.ma.array(u,mask=mask),np.ma.array(v,mask=mask),transform=vector_crs,
                  color=WHITE,length=4,linewidth=.5,barb_increments=dict(half=5,full=10,flag=50),
                  sizes=dict(emptybarb=.05,spacing=.16,height=.35),zorder=8)
    barbs.set_path_effects([effects.withStroke(linewidth=1.3,foreground='#080b09')])


def draw_dense_values(ax,scalar,x,y,source_crs,projection,usa,cities):
    xmin,xmax=ax.get_xlim();ymin,ymax=ax.get_ylim()
    xx,yy=np.meshgrid(np.arange(xmin+150000,xmax,210000),np.arange(ymin+150000,ymax,190000))
    coords=ccrs.PlateCarree().transform_points(projection,xx,yy)
    values=grid_sample(scalar,x,y,source_crs,projection,xx,yy)
    land=prep(usa)
    city_points=[projection.transform_point(lon,lat,ccrs.PlateCarree()) for _,lon,lat in cities]
    for px,py,lon,lat,value in zip(xx.flat,yy.flat,coords[...,0].flat,coords[...,1].flat,values.flat):
        if not np.isfinite(value) or not land.covers(Point(lon,lat)):continue
        # Reserve space for both the city name (extends east) and its value.
        if any(-140000<px-cx<420000 and -190000<py-cy<140000 for cx,cy in city_points):continue
        label=ax.text(px,py,f'{value:.0f}',ha='center',va='center',fontsize=7.5,weight='bold',
                      color=WHITE,transform=projection,zorder=7,clip_on=True)
        label.set_path_effects([effects.withStroke(linewidth=2.3,foreground='#080b09')])


REGIONS=[('conus','CONUS',-96,38,1),('carolinas','Carolinas',-79.8,35.4,4),
         ('southeast','Southeast',-84,33,2.3),('northeast','Northeast',-75,42,2.5),
         ('plains','Plains',-100,38,2.2),('west','West',-116,39,2.1)]


def region_presets(grid):
    projection=projection_for(grid);fig=plt.figure(figsize=(16,9))
    try:
        ax=fig.add_axes([.004,.055,.992,.874],projection=projection)
        ax.set_extent([-126,-65,23.5,50.5],crs=ccrs.PlateCarree());ax.apply_aspect()
        left,bottom,width,height=ax.get_position().bounds;xmin,xmax=ax.get_xlim();ymin,ymax=ax.get_ylim()
        result=[]
        for key,label,lon,lat,zoom in REGIONS:
            px,py=projection.transform_point(lon,lat,ccrs.PlateCarree())
            result.append(dict(id=key,label=label,zoom=zoom,x=(left+width*(px-xmin)/(xmax-xmin))*2400,y=(1-bottom-height*(py-ymin)/(ymax-ymin))*1350))
        return result
    finally:plt.close(fig)


def render(path,root,model,run,hour,fields,grid,geo,product='precip',overlay_only=False):
    config=PRODUCTS[product];lookup=None
    plt.rcParams.update({'font.family':'DejaVu Sans','text.color':WHITE,'font.size':9})
    figure=plt.figure(figsize=(16,9),dpi=150,facecolor=BG)
    try:
        projection=projection_for(grid)
        ax=figure.add_axes([.004,.055,.992,.874],projection=projection)
        ax.set_extent([-126,-65,23.5,50.5],crs=ccrs.PlateCarree())
        ax.set_facecolor('#141c19')
        land_artist=ax.add_geometries(geo['countries'],ccrs.PlateCarree(),facecolor='#232a26',edgecolor='#5d6c60',linewidth=.45,zorder=1)
        if product=='precip':kind,rate,rgba=classify(fields)
        else:
            scalar=scalar_field(fields,product)
            if product=='vort500':scalar=gaussian_filter(scalar,sigma=5 if model=='hrrr' else 1)
            cmap=LinearSegmentedColormap.from_list(product,config['colors'],N=256)
            norm=BoundaryNorm(config['levels'],cmap.N,extend='both')
            rgba=cmap(norm(scalar));rgba[~np.isfinite(scalar),3]=0
        pressure,thickness=diagnostics(fields)
        if grid['type']=='lambert':
            x,y=native_axes(grid,projection)
            # Native HRRR projection: retain every precipitation pixel without
            # reprojecting a million-cell categorical field for every frame.
            origin='lower' if grid['j_positive'] else 'upper'
            pixels=rgba[:,::-1] if grid['i_negative'] else rgba
            extent=[min(x)-grid['dx']/2,max(x)+grid['dx']/2,min(y)-grid['dy']/2,max(y)+grid['dy']/2]
            field_artist=ax.imshow(pixels,origin=origin,extent=extent,transform=projection,interpolation='nearest',zorder=2)
            step=4
            cx,cy=x[::step],y[::step]
            pres=gaussian_filter(pressure,sigma=3)[::step,::step]
            thick=gaussian_filter(thickness,sigma=3)[::step,::step]
            transform=projection
        else:
            x,y=grid['longitudes'],grid['latitudes']
            field_artist=ax.pcolormesh(x,y,rgba,transform=ccrs.PlateCarree(),shading='nearest',rasterized=True,zorder=2)
            cx,cy=x,y;pres=gaussian_filter(pressure,sigma=.6);thick=gaussian_filter(thickness,sigma=.6)
            transform=ccrs.PlateCarree()
        contours=[]
        if product=='precip':
            cold=ax.contour(cx,cy,thick,levels=np.arange(420,541,6),colors='#8FB3BC',linewidths=.7,linestyles='dashed',transform=transform,zorder=4)
            warm=ax.contour(cx,cy,thick,levels=np.arange(546,637,6),colors=GOLD,linewidths=.7,linestyles='dashed',transform=transform,zorder=4)
            solid=ax.contour(cx,cy,pres,levels=np.arange(872,1085,4),colors=WHITE,linewidths=.9,transform=transform,zorder=5)
            contours=[(cold,'#A8C6CD'),(warm,GOLD),(solid,WHITE)]
        elif product in ('wind500','vort500'):
            heights=gaussian_filter(fields['height500']/10,sigma=3 if grid['type']=='lambert' else .6)
            if grid['type']=='lambert':heights=heights[::4,::4]
            contour=ax.contour(cx,cy,heights,levels=np.arange(420,667,6),colors=WHITE,linewidths=.9,transform=transform,zorder=5)
            contours=[(contour,WHITE)]
        elif product=='mslp':
            contour=ax.contour(cx,cy,pres,levels=np.arange(872,1085,4),colors=WHITE,linewidths=.85,transform=transform,zorder=5)
            contours=[(contour,WHITE)]
        for contour,color in contours:
            labels=ax.clabel(contour,inline=True,fmt='%d',fontsize=6.8,colors=color,inline_spacing=3)
            for label in labels:label.set_path_effects([effects.withStroke(linewidth=1.6,foreground=BG)])
        for geometry,width in [(geo['countries'],.85),(geo['states'],.65),([geo['usa']],.95)]:
            boundaries=ax.add_geometries(geometry,ccrs.PlateCarree(),facecolor='none',edgecolor='#080b09',linewidth=width,zorder=6)
            boundaries.set_path_effects([effects.Stroke(linewidth=width+.45,foreground='#c4d0c740'),effects.Normal()])
        cities=[('Seattle',-122.33,47.61),('Los Angeles',-118.24,34.05),('Denver',-104.99,39.74),
             ('Dallas',-96.8,32.78),('Chicago',-87.63,41.88),('Charlotte',-80.84,35.23),('New York',-74.01,40.71),('Miami',-80.19,25.76)]
        if product in ('temp2m','dewpoint2m'):
            cities += [('Portland',-122.68,45.52),('San Francisco',-122.42,37.77),('Phoenix',-112.07,33.45),
                ('Salt Lake City',-111.89,40.76),('Minneapolis',-93.27,44.98),('Kansas City',-94.58,39.1),
                ('Houston',-95.37,29.76),('Atlanta',-84.39,33.75),('Boston',-71.06,42.36),('Washington',-77.04,38.91)]
        for name,lon,lat in cities:
            color=GOLD if name=='Charlotte' else WHITE
            ax.plot(lon,lat,'.',color=color,ms=2,transform=ccrs.PlateCarree(),zorder=7)
            label=ax.text(lon+.3,lat+.1,name,color=color,fontsize=6.4,transform=ccrs.PlateCarree(),zorder=7)
            label.set_path_effects([effects.withStroke(linewidth=2,foreground=BG)])
            if product in ('temp2m','dewpoint2m'):
                px,py=projection.transform_point(lon,lat,ccrs.PlateCarree())
                value=float(grid_sample(scalar,x,y,transform,projection,np.array([px]),np.array([py]))[0])
                if np.isfinite(value):
                    text=ax.annotate(f'{value:.0f}°',xy=(lon,lat),xycoords=ccrs.PlateCarree()._as_mpl_transform(ax),
                        xytext=(4,-11),textcoords='offset points',ha='left',va='center',color=WHITE,fontsize=10,weight='bold',zorder=9,clip_on=True)
                    text.set_path_effects([effects.withStroke(linewidth=2.8,foreground=BG)])
        if product=='precip':
            draw_pressure_centers(ax,pres,cx,cy,transform,projection)
            if not overlay_only and {'temperature2','dewpoint2'}<=set(fields):lookup=write_readouts(path,ax,fields,x,y,transform,projection)
        elif product in ('temp2m','dewpoint2m'):
            draw_dense_values(ax,scalar,x,y,transform,projection,geo['usa'],cities)
            if not overlay_only and model=='nam' and product=='temp2m':lookup=write_readouts(path,ax,fields,x,y,transform,projection)
        elif product=='wind500':draw_wind_barbs(ax,grid,x,y,fields,projection,transform)
        elif product=='wind10':draw_wind_barbs(ax,grid,x,y,fields,projection,transform,level='10')
        elif product=='mslp':draw_pressure_centers(ax,pres,cx,cy,transform,projection)
        ax.spines['geo'].set_edgecolor('#536657')
        logo=figure.add_axes([.007,.938,.04,.055]);logo.axis('off');logo.imshow(Image.open(root/'assets/ch-weather-logo.png'))
        valid=run+timedelta(hours=hour)
        figure.text(.055,.967,model.upper()+'  /  '+config['title'],fontsize=14,weight='bold')
        figure.text(.055,.944,config['subtitle'],fontsize=7.2,color=GOLD)
        figure.text(.99,.968,f'VALID {valid:%a %b %d, %Y  %H:%M} UTC',ha='right',fontsize=10,weight='bold')
        figure.text(.99,.946,f'INIT {run:%Y-%m-%d %H}Z  /  F{hour:03d}  /  '+{'gfs':'0.25° GFS','hrrr':'3 KM HRRR','nam':'12 KM NAM'}[model],ha='right',fontsize=8,color=SAGE)
        figure.add_artist(plt.Line2D([.004,.996],[.934,.934],color=GREEN,lw=1,transform=figure.transFigure))
        if product=='precip':
            for i,(name,color) in enumerate(zip(TYPE_NAMES[1:],TYPE_COLORS[1:])):
                pos=.012+i*.108
                figure.add_artist(Rectangle((pos,.022),.009,.012,facecolor=color,transform=figure.transFigure))
                figure.text(pos+.013,.023,name,fontsize=7)
            figure.text(.99,.027,'RATE SHADING ≥0.1 mm/h · BRIGHTER = HEAVIER',fontsize=7,color=SAGE,ha='right')
        else:
            color_axis=figure.add_axes([.1,.031,.61,.012])
            bar=figure.colorbar(ScalarMappable(norm=norm,cmap=cmap),cax=color_axis,orientation='horizontal',extend='both')
            bar.ax.tick_params(labelsize=6.5,length=2,pad=2,color=SAGE,labelcolor=WHITE)
            figure.text(.013,.031,config['unit'],fontsize=8,color=WHITE)
            context={'temp2m':'2 M ABOVE GROUND','dewpoint2m':'2 M ABOVE GROUND','rh2m':'2 M ABOVE GROUND','wind10':'10 M ABOVE GROUND','mslp':'REDUCED TO SEA LEVEL','sbcape':'SURFACE PARCEL / BUOYANCY'}
            figure.text(.99,.027,'MODEL GUIDANCE · '+context.get(product,'500 MB / APPROX. 18,000 FT'),fontsize=7,color=SAGE,ha='right')
        figure.text(.012,.005,'NOAA/NCEP model guidance · Natural Earth · CH Weather / Christopher Horne',fontsize=6.5,color=SAGE)
        figure.text(.99,.005,'Not an official warning or forecast',fontsize=6.5,color=SAGE,ha='right')
        if not overlay_only:figure.savefig(path,dpi=150,facecolor=BG)
        overlay=None
        if product!='precip':
            field_artist.set_visible(False);land_artist.set_facecolor('none')
            overlay_path=Path(path).with_name(Path(path).stem+'-overlay.png')
            figure.savefig(overlay_path,dpi=150,transparent=True)
            with Image.open(overlay_path) as source:
                optimized_overlay=source.convert('RGBA').quantize(colors=256,method=Image.Quantize.FASTOCTREE)
            webp_path=overlay_path.with_suffix('.webp')
            optimized_overlay.convert('RGBA').save(webp_path,format='WEBP',lossless=True,method=2)
            overlay_path.unlink();overlay_path=webp_path
            overlay=dict(filename=overlay_path.name)
    finally:plt.close(figure)
    if not overlay_only:
        with Image.open(path) as image:
            if image.size!=(2400,1350):raise ValueError('Incorrect model graphic dimensions')
            optimized=image.convert('RGB').quantize(colors=256,method=Image.Quantize.FASTOCTREE)
        optimized.save(path,optimize=True)
    return dict(readouts=lookup,overlay=overlay)
