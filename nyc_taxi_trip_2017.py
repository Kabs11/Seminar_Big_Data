import shapefile
from shapely.geometry import Polygon
from descartes.patch import PolygonPatch
import matplotlib as mpl
import matplotlib.pyplot as plt
plt.style.use('ggplot')
from collections import Counter
import pandas as pd
import numpy as np
from operator import itemgetter


df = pd.read_csv('green_tripdata_2017-12.csv')
df_zone = pd.read_csv('taxi+_zone_lookup.csv')

df_zone = df_zone.drop(['service_zone'],axis=1)
df = df.drop(['fare_amount','store_and_fwd_flag','RatecodeID','tip_amount','mta_tax','extra','ehail_fee','tolls_amount','lpep_dropoff_datetime','payment_type','trip_type','total_amount','lpep_pickup_datetime','improvement_surcharge'],axis=1)
df_zone = df_zone.drop_duplicates('Zone')
df_zone = df_zone.reset_index()

PUs = Counter(df['PULocationID'])
DOs = Counter(df['DOLocationID'])
PU_ID = list(PUs.keys())
PU_count = list(PUs.values())
DO_ID = list(DOs.keys())
DO_count = list(DOs.values())

combo1 = []
for x in range(len(PU_ID)):
    for y in range(len(DO_ID)):
        if(PU_ID[x] == DO_ID[y]):
            sum = PU_count[x] + DO_count[y]
            combo1.append((PU_ID[x],sum))

combo1 = sorted(combo1, key=lambda x: x[1],reverse=True)
combo1 = combo1[:5]
combo1_id = list(map(itemgetter(0), combo1))
combo1_counts = list(map(itemgetter(1), combo1))
location = []
for z in range(len(combo1_id)):
    for a in range(len(df_zone['LocationID'])):
        if(combo1_id[z] == df_zone['LocationID'][a]):
           location.append(df_zone['Borough'][a])
           print(combo1_counts[z],' pick-ups and drop-offs found at',df_zone['Zone'][a],' Zone ID:',combo1_id[z])


def get_boundaries(sf):
    lat, lon = [], []
    for shape in list(sf.iterShapes()):
        lat.extend([shape.bbox[0], shape.bbox[2]])
        lon.extend([shape.bbox[1], shape.bbox[3]])

    margin = 0.01 # buffer to add to the range
    lat_min = min(lat) - margin
    lat_max = max(lat) + margin
    lon_min = min(lon) - margin
    lon_max = max(lon) + margin

    return lat_min, lat_max, lon_min, lon_max


def draw_zone_map(ax, sf, heat={}, text=[], arrows=[]):
    continent = [235 / 256, 151 / 256, 78 / 256]
    ocean = (89 / 256, 171 / 256, 227 / 256)
    theta = np.linspace(0, 2 * np.pi, len(text) + 1).tolist()
    ax.set_facecolor(ocean)

    # colorbar
    if len(heat) != 0:
        norm = mpl.colors.Normalize(vmin=min(heat.values()),
                                    vmax=max(heat.values()))  # norm = mpl.colors.LogNorm(vmin=1,vmax=max(heat))
        cm = plt.get_cmap('Reds')
        sm = plt.cm.ScalarMappable(cmap=cm, norm=norm)
        sm.set_array([])
        plt.colorbar(sm, ticks=np.linspace(min(heat.values()), max(heat.values()), 8),
                     boundaries=np.arange(min(heat.values()) - 10, max(heat.values()) + 10, .1))

    for sr in sf.shapeRecords():
        shape = sr.shape
        rec = sr.record
        loc_id = rec[shp_dic['LocationID']]
        zone = rec[shp_dic['zone']]

        if len(heat) == 0:
            col = continent
        else:
            if loc_id not in heat:
                R, G, B, A = cm(norm(0))
            else:
                R, G, B, A = cm(norm(heat[loc_id]))
            col = [R, G, B]

        # check number of parts (could use MultiPolygon class of shapely?)
        nparts = len(shape.parts)  # total parts
        if nparts == 1:
            polygon = Polygon(shape.points)
            patch = PolygonPatch(polygon, facecolor=col, alpha=1.0, zorder=2)
            ax.add_patch(patch)
        else:  # loop over parts of each shape, plot separately
            for ip in range(nparts):  # loop over parts, plot separately
                i0 = shape.parts[ip]
                if ip < nparts - 1:
                    i1 = shape.parts[ip + 1] - 1
                else:
                    i1 = len(shape.points)

                polygon = Polygon(shape.points[i0:i1 + 1])
                patch = PolygonPatch(polygon, facecolor=col, alpha=1.0, zorder=2)
                ax.add_patch(patch)

        x = (shape.bbox[0] + shape.bbox[2]) / 2
        y = (shape.bbox[1] + shape.bbox[3]) / 2
        if (len(text) == 0 and rec[shp_dic['Shape_Area']] > 0.0001):
            plt.text(x, y, str(loc_id), horizontalalignment='center', verticalalignment='center')
        elif len(text) != 0 and loc_id in text:
            # plt.text(x+0.01, y-0.01, str(loc_id), fontsize=12, color="white", bbox=dict(facecolor='black', alpha=0.5))
            eta_x = 0.05 * np.cos(theta[text.index(loc_id)])
            eta_y = 0.05 * np.sin(theta[text.index(loc_id)])
            ax.annotate("[{}] {}".format(loc_id, zone), xy=(x, y), xytext=(x + eta_x, y + eta_y),
                        bbox=dict(facecolor='black', alpha=0.5), color="white", fontsize=8,
                        arrowprops=dict(facecolor='black', width=3, shrink=0.05))
    if len(arrows) != 0:
        for arr in arrows:
            ax.annotate('', xy=arr['dest'], xytext=arr['src'], size=arr['cnt'],
                        arrowprops=dict(arrowstyle="fancy", fc="0.6", ec="none"))

    # display
    limits = get_boundaries(sf)
    plt.xlim(limits[0], limits[1])
    plt.ylim(limits[2], limits[3])
    plt.show()

def get_lat_lon(sf):
    content = []
    for sr in sf.shapeRecords():
        shape = sr.shape
        rec = sr.record
        loc_id = rec[shp_dic['LocationID']]

        x = (shape.bbox[0] + shape.bbox[2]) / 2
        y = (shape.bbox[1] + shape.bbox[3]) / 2

        content.append((loc_id, x, y))
    return pd.DataFrame(content, columns=["LocationID", "longitude", "latitude"])
sf = shapefile.Reader("taxi_zones/taxi_zones.shp")
fields_name = [field[0] for field in sf.fields[1:]]
shp_dic = dict(zip(fields_name, list(range(len(fields_name)))))
attributes = sf.records()
shp_attr = [dict(zip(fields_name, attr)) for attr in attributes]

df_loc = pd.DataFrame(shp_attr).join(get_lat_lon(sf).set_index("LocationID"), on="LocationID")
fig, ax = plt.subplots(figsize=(50,50))
ax = plt.subplot(1, 2, 2)
ax.set_title("Zones in NYC")
draw_zone_map(ax, sf)

