"""Model-map definitions and explicit meteorological display units."""
import numpy as np

PRODUCTS={
    'precip':dict(label='Precip type + pressure',title='PRECIP TYPE + PRESSURE',subtitle='1000–500 MB THICKNESS (DASHED) · MEAN SEA-LEVEL PRESSURE (SOLID)'),
    'temp2m':dict(label='2 m temperature',title='2 M TEMPERATURE',subtitle='FAHRENHEIT · NEAREST MODEL-GRID CITY READOUTS',unit='°F',levels=list(range(-40,125,5)),colors=['#65518c','#476eab','#64a9c5','#77bfba','#8cb985','#d0c46e','#d69a58','#bc6352','#a44055']),
    'dewpoint2m':dict(label='2 m dewpoint',title='2 M DEWPOINT',subtitle='FAHRENHEIT · NEAREST MODEL-GRID CITY READOUTS',unit='°F',levels=list(range(-30,95,5)),colors=['#795d53','#a38564','#c3b98c','#a8b59a','#73aa87','#408f74','#217c79','#3f758e','#726a9d']),
    'wind500':dict(label='500 mb heights + wind',title='500 MB HEIGHTS + WIND',subtitle='HEIGHTS: 6 DAM CONTOURS · WIND SHADING + BARBS: KNOTS',unit='kt',levels=list(range(0,181,10)),colors=['#202b29','#396457','#74a58c','#b0c09a','#d59a53','#c76c50','#ac4b6c','#816c9e']),
    'vort500':dict(label='500 mb absolute vorticity',title='500 MB ABSOLUTE VORTICITY',subtitle='ABSOLUTE VORTICITY: 10⁻⁵ s⁻¹ · HEIGHTS: 6 DAM CONTOURS',unit='10⁻⁵ s⁻¹',levels=[-30,-20,-10,0,4,8,12,16,20,24,28,32,40,50,65,80],colors=['#526f9a','#719aa7','#283934','#9c9d66','#d0b45d','#d69047','#c66242','#ad494b','#8b4c70']),
}

PRODUCTS.update({
    'wind10':dict(label='10 m sustained wind',title='10 M SUSTAINED WIND',subtitle='MODEL WIND SPEED + BARBS: KNOTS · NOT GUST SPEED',unit='kt',levels=list(range(0,105,5)),colors=['#202b29','#396457','#74a58c','#b0c09a','#d2bb72','#d59a53','#c76c50','#ac4b6c','#816c9e']),
    'rh2m':dict(label='2 m relative humidity',title='2 M RELATIVE HUMIDITY',subtitle='MODEL RELATIVE HUMIDITY · PERCENT',unit='%',levels=list(range(0,101,10)),colors=['#795d53','#a38564','#c3b98c','#a8b59a','#73aa87','#408f74','#217c79']),
    'mslp':dict(label='Mean sea-level pressure',title='MEAN SEA-LEVEL PRESSURE',subtitle='PRESSURE: hPa / mb · 4 hPa CONTOURS · SELECTED HIGH / LOW CENTERS',unit='hPa',levels=list(range(960,1061,4)),colors=['#64517e','#5b7c9d','#6badaf','#91b295','#c4bc86','#d3a767','#b67455']),
    'sbcape':dict(label='Surface-based CAPE',title='SURFACE-BASED CAPE',subtitle='MODEL SURFACE PARCEL CAPE · J/kg · NOT A SEVERE-WEATHER PROBABILITY',unit='J/kg',levels=[0,100,250,500,750,1000,1500,2000,2500,3000,4000,5000,6000],colors=['#202b29','#396457','#74a58c','#b0c09a','#d2bb72','#d59a53','#c76c50','#ac4b6c','#816c9e']),
})


def available_products(model):
    return [key for key in PRODUCTS if not (model=='nam' and key=='precip')]


def parameter_metadata():
    from matplotlib.colors import LinearSegmentedColormap,BoundaryNorm,to_hex
    from .product import TYPE_COLORS,TYPE_NAMES
    result=[]
    for key,config in PRODUCTS.items():
        item=dict(id=key,label=config['label'],description=config['subtitle'])
        if key=='precip':item['legend']=[dict(label=name,color=color) for name,color in zip(TYPE_NAMES[1:],TYPE_COLORS[1:])]
        else:
            cmap=LinearSegmentedColormap.from_list(key,config['colors'],N=256);norm=BoundaryNorm(config['levels'],cmap.N,extend='both')
            levels=config['levels'];item.update(unit=config['unit'],levels=levels,
                swatches=[to_hex(cmap(norm((a+b)/2))) for a,b in zip(levels[:-1],levels[1:])])
        result.append(item)
    return result


def scalar_field(fields,product):
    if product=='wind10':return np.hypot(fields['u10'],fields['v10'])*1.94384449244
    if product=='rh2m':return fields['humidity2']
    if product=='mslp':return fields['pressure']/100
    if product=='sbcape':return fields['cape']
    if product=='temp2m':return (fields['temperature2']-273.15)*1.8+32
    if product=='dewpoint2m':return (fields['dewpoint2']-273.15)*1.8+32
    if product=='wind500':return np.hypot(fields['u500'],fields['v500'])*1.94384449244
    if product=='vort500':return fields['vorticity500']*100000
    raise ValueError('Unknown scalar map product: '+str(product))
