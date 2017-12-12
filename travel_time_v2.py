import os
import json
from flask import jsonify
import gdal, osr, ogr
import numpy as np
from skimage import graph
import psycopg2

import time
start = time.time()

#
# function to clear all output folders of previously produced files
#
def empty_folders():
	raster_files_to_delete = os.listdir("opt/geoserver/data_dir/produced_rasters") # Empty output folders of previously produced files
	for raster in raster_files_to_delete:
		os.remove(os.path.join("opt/geoserver/data_dir/produced_rasters",raster))
	shape_files_to_delete = os.listdir("opt/geoserver/data_dir/produced_shapefiles") # Empty output folders of previously produced files
	for shape in shape_files_to_delete:
		os.remove(os.path.join("opt/geoserver/data_dir/produced_shapefiles", shape))
	binary_raster_to_delete = os.listdir("output/")
	for raster in binary_raster_to_delete:
		os.remove(os.path.join("output", raster))

#
# function to return names of variables, file names and database table names from arguments passed from AJAX
#
def define_variables(country_chosen, travel_method):
	CostSurfacefn = "rasters/" + country_chosen.upper() + "/" + country_chosen.upper() + "_" + travel_method + "_friction.tif" #Cost raster for chosen country and travel method
	empty_folders()
	raster_bin = "output/" + country_chosen + "_raster_bin.tif" # Binary output raster
	raster_cont = "opt/geoserver/data_dir/produced_rasters/" + country_chosen + "_raster_cont.tif" # Continous output raster -> Needs to be displayed in Geoserver
	shp_bin = "opt/geoserver/data_dir/produced_shapefiles/" + country_chosen + "_shp_bin.shp" # Binary shp polygon showing pop inside travel time -> Needs to go to postgis and geoserver
	postgis_table = country_chosen + "_travel_costs_polygon"
	return CostSurfacefn, raster_bin, raster_cont, shp_bin, postgis_table

#
# function to open cost raster, make arrays which will hold costs, and geo information help in cost raster
#
def open_ds_and_array(CostSurfacefn):
	in_ds = gdal.Open(CostSurfacefn)
	in_band = in_ds.GetRasterBand(1)
	geotransform = in_ds.GetGeoTransform()
	costarray = in_band.ReadAsArray()
	holder_array = np.zeros_like(costarray, dtype=np.int32)
	costDistMCP = graph.MCP_Geometric(costarray, fully_connected=True)
	return in_ds, in_band, geotransform, costarray, holder_array, costDistMCP


#
# function converts a list of WGS84 coordinates into geotransformed array indices within the cost surface array
#
def get_offsets(startCoord, geotransform):
	hosp_offset = []
	originX = geotransform[0]
	originY = geotransform[3]
	pixelWidth = geotransform[1]
	pixelHeight = geotransform[5]
	for coord in startCoord:
		xOffset = int((coord[0] - originX)/pixelWidth)
		yOffset = int((coord[1] - originY)/pixelHeight)
		xy = (yOffset, xOffset) 
		hosp_offset.append(xy)
	return hosp_offset

#
# function gets cost for each pixel to each hospital as lists, lists are stacked and minimum values are returned as list
# 
def get_costs(holder_array, hosp_offset, costDistMCP, num_hours):
	cost_arrays = [] #list to hold cost arrays for each hospital. These will be stacked later and minimum values extraced
	for i in hosp_offset:
		cumcostdist, trace2 = costDistMCP.find_costs([i])
		holder_array = np.asarray(cumcostdist)
		cost_arrays.append(np.copy(holder_array))
		#del cumcostdist, trace2, holder_array
		#print "holder_array shape: {0}".format(holder_array.shape)
	#print len(cost_arrays)
	stack = np.stack(cost_arrays, axis=2)
	cum_cost_array_cont = stack.min(axis=2)
	#print "cum_cost_array shape: {0}".format(cum_cost_array.shape)
	#cum_cost_array = np.ma.masked_outside(cum_cost_array, 0, 120)
	cum_cost_array_bin = np.where(cum_cost_array_cont <= ((num_hours*60)+1), 1, 0)
	print cum_cost_array_cont
	return cum_cost_array_cont, cum_cost_array_bin

#
# Build output rasters filling them with cost-distance arrays. This function creates a binary AND continuous raster (Binary for zonal stats; Continuous for frontend display)
#
def build_rasters(in_ds, in_band, geotransform, raster_cont, raster_bin, cum_cost_array_cont, cum_cost_array_bin):
	gtiff = gdal.GetDriverByName('GTiff')

	###########CONTINUOUS RASTER#####################
	out_ds_cont = gtiff.Create(raster_cont, in_band.XSize, in_band.YSize, 1, gdal.GDT_UInt32)
	out_ds_cont.SetProjection(in_ds.GetProjection())
	out_ds_cont.SetGeoTransform(geotransform)
	out_band_cont = out_ds_cont.GetRasterBand(1)
	out_band_cont.SetNoDataValue(255)
	out_band_cont.WriteArray(cum_cost_array_cont)
	out_ds_cont.FlushCache()

	##########BINARY RASTER###########################
	out_ds_bin = gtiff.Create(raster_bin, in_band.XSize, in_band.YSize, 1, gdal.GDT_UInt32)
	out_ds_bin.SetProjection(in_ds.GetProjection())
	out_ds_bin.SetGeoTransform(geotransform)
	out_band_bin = out_ds_bin.GetRasterBand(1)
	out_band_bin.SetNoDataValue(255)
	out_band_bin.WriteArray(cum_cost_array_bin)
	out_ds_bin.FlushCache()


#
# Polygonise binary raster to be posted to PostGIS for zonal stats analysis
#
def polygonise_travel_times(raster, shp_bin):
	latlong = osr.SpatialReference()
	latlong.ImportFromEPSG( 4326 )
	polygon = shp_bin.encode('utf-8')
	in_poly_ds = gdal.Open(raster)
	polygon_band = in_poly_ds.GetRasterBand(1)
	drv = ogr.GetDriverByName("ESRI Shapefile")
	dst_ds = drv.CreateDataSource(polygon)
	dst_layer = dst_ds.CreateLayer(polygon, srs=latlong)
	newField = ogr.FieldDefn('Value', ogr.OFTInteger)
	dst_layer.CreateField(newField)
	#gdal.Polygonize(polygon_band, None, dst_layer, -1, ["value"], callback=None)
	gdal.Polygonize(polygon_band, None, dst_layer, 0, [], callback=None)


#
# Export shapefile to PostGIS container, analyse zonal stats against population within and outside 2-hour from hostpital threshold.
#
def shp_to_postGIS(postgis_table, shp_bin, country_chosen, population_chosen):
	try:
		connection = psycopg2.connect("dbname='gis' user='postgres' host='172.17.0.3' password='<PASSWORD>'")
		print "Connection made"

	except:
		print "Can't connect to the database"

	cursor = connection.cursor()

	cursor.execute("DROP TABLE IF EXISTS {0}".format(postgis_table))
	print "executed"
	cursor.execute("""CREATE TABLE {0} (
						id SERIAL,
						value integer,
						PRIMARY KEY (id))
					""".format(postgis_table))
	cursor.execute("DROP INDEX IF EXISTS levelIndex;")
	cursor.execute("DROP INDEX IF EXISTS geomIndex;")
	cursor.execute("CREATE INDEX levelIndex ON {0}(value)".format(postgis_table))
	cursor.execute("SELECT AddGeometryColumn('{0}', ".format(postgis_table) +
								"'geom', 4326, 'POLYGON', 2)")
	cursor.execute("CREATE INDEX geomIndex ON {0} ".format(postgis_table) +
					"USING GIST (geom)")
	connection.commit()
	for pol in [0,1]:
		fName = shp_bin
		shapefile = ogr.Open(fName)
		layer = shapefile.GetLayer(0)
		for i in range(layer.GetFeatureCount()):
			feature = layer.GetFeature(i)
			if feature.GetField('Value') == 1:
				geometry = feature.GetGeometryRef()
				wkt = geometry.ExportToWkt()
				cursor.execute("INSERT INTO {0} (value, geom) ".format(postgis_table) +
								"VALUES (%s, ST_GeomFromText(%s, " +
								"4326))", (pol, wkt))
				connection.commit()

	old_level = connection.isolation_level
	connection.set_isolation_level(0)
	cursor.execute("VACUUM ANALYZE")
	##################################Zonal Stats##################################
	cursor.execute("DROP TABLE IF EXISTS travel_polygons;")
	cursor.execute("DROP index IF EXISTS travel_polygons_geom;")
	cursor.execute("CREATE TABLE travel_polygons AS (SELECT (st_dump(geom)).geom geom FROM {0} WHERE value =1);".format(postgis_table))
	cursor.execute("CREATE index travel_polygons_geom on travel_polygons using gist(geom);")
	cursor.execute("DROP TABLE IF EXISTS travel_inter_adm1;")
	cursor.execute("CREATE table travel_inter_adm1 AS(SELECT st_intersection({0}_adm1.geom,travel_polygons.geom) as geom, name_1 as \
	     travel_in_state FROM travel_polygons inner join {0}_adm1 on st_intersects(travel_polygons.geom, {0}_adm1.geom));".format(country_chosen))
	cursor.execute("CREATE index travel_inter_adm1_geom on travel_inter_adm1 using gist(geom);")
	cursor.execute("ALTER table travel_inter_adm1 ADD COLUMN key_column BIGSERIAL PRIMARY KEY;")

	cursor.execute("DROP TABLE IF EXISTS zonal_stats_{0};".format(country_chosen))
	cursor.execute("DROP TABLE IF EXISTS {0}_{1}_total".format(country_chosen, population_chosen))
	cursor.execute("CREATE TABLE {0}_{1}_total AS (select distinct (name_1), SUM((ST_SUMMARYStats(a.rast)).sum) as population from {0}_{1} AS a, \
		    {0}_adm1 AS b WHERE ST_Intersects(b.geom, a.rast)GROUP BY name_1)".format(country_chosen, population_chosen))
	cursor.execute("CREATE TABLE zonal_stats_{0} AS (SELECT distinct(travel_in_state), (SUM(ST_SUMMARYStats(St_clip(rast,geom)))).sum\
	     AS pop_inside_2hrs FROM {0}_{1} INNER JOIN travel_inter_adm1 ON ST_Intersects(travel_inter_adm1.geom, rast) GROUP BY travel_in_state);".format(country_chosen, population_chosen))
	cursor.execute("ALTER TABLE zonal_stats_{0} ADD COLUMN total_pop numeric,ADD COLUMN pop_outside_2hrs numeric, ADD COLUMN percent_without_access numeric;".format(country_chosen))
	cursor.execute("UPDATE zonal_stats_{0} b SET total_pop = a.population FROM {0}_{1}_total a WHERE b.travel_in_state = a.name_1;".format(country_chosen, population_chosen))
	cursor.execute("UPDATE zonal_stats_{0} SET pop_outside_2hrs = total_pop - pop_inside_2hrs, percent_without_access = ((total_pop - pop_inside_2hrs)/total_pop)*100".format(country_chosen))
	connection.set_isolation_level(old_level)


#
# Function to extract zonal stats table from PostGIS and return to frontend as JSON
#
def get_zonal_stats(country_chosen):
	try:
		connection = psycopg2.connect("dbname='gis' user='postgres' host='172.17.0.3' password='<PASSWORD>'")
		print "Connection made"

	except:
		print "Can't connect to the database"
	old_level = connection.isolation_level
	connection.set_isolation_level(0)
	cursor = connection.cursor()
	cursor.execute("SELECT row_to_json(zonal_stats_{0}) as json FROM public.zonal_stats_{0}".format(country_chosen))
	# columns = ('travel_in_state', 'pop_inside_2hrs', 'total_pop', 'pop_outside_2hrs', 'percent_without_access')
	# results = []
	# for row in cursor.fetchall():
	# 	results.append(dict(zip(columns, row)))
	query = cursor.fetchall()
	results = json.dumps(query)
	connection.set_isolation_level(old_level)
	return results	



#
# Main arguments passsed from the Flask app to be processed by various functions
#
def main(startCoord, num_hours, travel_method, country_chosen, population_chosen):
	CostSurfacefn, raster_bin, raster_cont, shp_bin, postgis_table = define_variables(country_chosen, travel_method)
	in_ds, in_band, geotransform, costarray, holder_array, costDistMCP = open_ds_and_array(CostSurfacefn)
	hosp_offset = get_offsets(startCoord, geotransform) #list to hold offsets within array converted from coordinates
	cum_cost_array_cont, cum_cost_array_bin = get_costs(holder_array, hosp_offset, costDistMCP, num_hours) #list holding cumulative time cost from every pixel to hospital with lowest time cost 
	build_rasters(in_ds, in_band, geotransform, raster_cont, raster_bin, cum_cost_array_cont, cum_cost_array_bin)
	polygonise_travel_times(raster_bin, shp_bin)
	shp_to_postGIS(postgis_table, shp_bin, country_chosen, population_chosen) #<-------------IS THIS TO BE POSTGIS OR GEOPANDAS
	zonal_stats = get_zonal_stats(country_chosen)
	return zonal_stats


print 'It took ', time.time() - start, ' seconds.'

