/*Javascript v3 of Alpha 
* Methods to initialise map and carry out functions
* These functions attempt to add vector and raster layers as WMS
*/


/*Bing satellite map API key*/
var apiKey ='AsITKrfH_sDI9TfdJEl4A-kGG_QqNCaXLe80R_kyLWoyHMgnzpTB1BYxHxDVT1TA';

function initialiseMap() {
	
	/* ++++++++++++++++++++++++++++Variable to set up the map ++++++++++++++++++++++++++++++++++*/
	
	/*OSM tile layer*/
	var OSMTiles = new ol.layer.Tile({
		title: 'Open Street Map',
		source: new ol.source.OSM(),
	});
	
	/*Bing satellite tile layer*/
	var bingSatellite = new ol.layer.Tile({
		title: 'Bing Satellite',
		source: new ol.source.BingMaps({
			key: apiKey,
			imagerySet: 'AerialWithLabels'
		}),
		
	});
	
	
	
	
	/*Layer to hold points with styling*/
	var pointVectorLayer = new ol.layer.Vector ({
		source: new ol.source.Vector ({
		}),
		style: new ol.style.Style ({
			image: new ol.style.Circle ({
				fill: new ol.style.Fill ({
					color: 'red'
				}),
				stroke: new ol.style.Stroke ({
					color: 'black',
					width: 1
				}),
				radius: 6
			})
		})
	});
	
	pointVectorLayer.setZIndex(3);
	
	/* Map view */
	var view = new ol.View({
		center: ol.proj.fromLonLat([25.4, -1.32]),
		zoom: 4,
		maxZoom: 20
	});
	
	/*Attribution for overview map ++++++++++++++++++++++++++++This isn't showing anywhere*/
	var attribution = new ol.Attribution({
	  html: 'Tiles &copy; <a href="http://services.arcgisonline.com/ArcGIS/' +
		  'rest/services/World_Topo_Map/MapServer">ArcGIS</a>'
	});


	/* On-map controls (zoom, map overview etc) */
	var controls =  ol.control.defaults().extend([
			new ol.control.FullScreen(),
			new ol.control.MousePosition({
				coordinateFormat: ol.coordinate.createStringXY(2),
				projection: 'EPSG:4326'
			}),
			new ol.control.OverviewMap({
				collapsed: false, 
				collapsible: false,
				className: 'ol-overviewmap ol-custom-overviewmap',
				layers: [
					new ol.layer.Tile({
						source: new ol.source.XYZ({
							url: 'http://server.arcgisonline.com/ArcGIS/rest/services/' +
								'World_Topo_Map/MapServer/tile/{z}/{y}/{x}'
						})
					})
					],
				attibutions: [attribution]
			}),
			new ol.control.ScaleLine(),
			new ol.control.ZoomSlider(),
		]);



	/*Add slider to control the opacity of the satellite layer in order to see the OSM layer*/
	var $opacity = $('#js-opacity');

	$('#js-slider').slider({
		min: 0,
		max: 100,
		value: 100,
		slide: function(event, ui) {
			$opacity.text(ui.value + '%');
			map.getLayers().item(1).setOpacity(ui.value / 100);
		}
	});
		
	
	/*Create a list of layers to be added to the map */
	var mapLayers = [OSMTiles, bingSatellite, pointVectorLayer];
	
	/* Instantiate the map */
	var map = new ol.Map({
		target: 'map',
		layers: mapLayers,
		view: view,
		controls: controls,
		interactions : ol.interaction.defaults({doubleClickZoom :false}),	
	});


	/************************************CODE TO ADD LAYERS FROM POSTGIS/GEOSERVER *********************************/
	/*+++++++++++++++++++++++++++++++++++++++++COUNTRY SELECT+++++++++++++++++++++++++++++++++++++++++++++++++++*/
	var country_L1;
	var country_selected = false;
	var country;

	$(document).ready(function() {

	$("#country_select").on('change',function() {

			country = $(this).find("option:selected").attr("id");
			console.log(country);
			if (country != "none_chosen") {
				country_selected = true;
			} else {
				country_selected = false;
			};

			var layer = 'dissertation:' + country;
			if (country_L1) {
				map.removeLayer(country_L1);
				map.removeLayer(pop_raster);
				$("#raster_select").get(0).selectedIndex = 0;
			};
			country_L1 = new ol.layer.Tile({
				source: new ol.source.TileWMS({
					url: 'http://172.17.0.2:8080/geoserver/dissertation/wms',
					params: {'FORMAT': 'image/png', 
		                   'VERSION': '1.1.1',
		                   tiled: true,
		                STYLES: '',
		                LAYERS: layer,
		            
		          }
				})
			});
			map.addLayer(country_L1);
			country_L1.setZIndex(2);

			
		});

});	
	/*+++++++++++++++++++++++++++++++++++++++++COUNTRY SELECT+++++++++++++++++++++++++++++++++++++++++++++++++++*/

	/************************ADD POPULATION RASTER ***********************************/

	var pop_raster;
	var raster_selected = false;


	$(document).ready(function() {
		$("#raster_select").on('change', function() {
			if (!country_selected) {
				alert("Please first select a country");
			} 
			if (pop_raster) {
				map.removeLayer(pop_raster);
			};

			var raster_layer = country.slice(0,-5).toUpperCase() + $("#raster_select").find("option:selected").attr("id");

			if ($("#raster_select").find("option:selected").attr("id") != "no_pop_chosen") {
				raster_selected = true;
			} else {
				raster_selected = false;
			};

			pop_raster = new ol.layer.Tile({
				source: new ol.source.TileWMS({
					url: 'http://172.17.0.2:8080/geoserver/dissertation/wms',
					params: {'FORMAT': 'image/png',
							'VERSION': '1.1.1',
							tiled: true,
							STYLES: '',
							LAYERS: raster_layer
						}
				})
			});
			map.addLayer(pop_raster);
			pop_raster.setZIndex(1);
			console.log(raster_layer);
		})
	});
	/************************ADD POPULATION RASTER ***********************************/


	/***********************************ADD IMPEDANCE SURFACE RASTER *********************************************/

	var impedance_raster;
	var impedance_selected = false;
	$(document).ready(function() {
		$("#impedance_select").on('change', function() {
			if (!country_selected) {
				alert("Please first select a country");
			} 
			if (impedance_raster) {
				map.removeLayer(impedance_raster);
			};

			var impedance_layer = country.slice(0,-5).toUpperCase() + "_friction";

			if ($("#impedance_select").find("option:selected").attr("id") != "no_pop_chosen") {
				raster_selected = true;
			} else {
				raster_selected = false;
			};

			impedance_raster = new ol.layer.Tile({
				source: new ol.source.TileWMS({
					url: 'http://172.17.0.2:8080/geoserver/dissertation/wms',
					params: {'FORMAT': 'image/png',
							'VERSION': '1.1.1',
							tiled: true,
							STYLES: '',
							LAYERS: impedance_layer
						}
				})
			});
			map.addLayer(impedance_raster);
			pop_raster.setZIndex(1);
			console.log(impedance_layer);
		})
	});




	
	/***********************************END OF CODE TO ADD LAYERS FROM POSTGIS/GEOSERVER ***************************/



	
	/* BUTTON TO Remove points using overlay +++++++++++++++++++++++++++++++++++++++++++++++++++ */
	 var delOverlay = new ol.Overlay({
	 	element: document.getElementById("js-overlay")
	 });

	 map.addOverlay(delOverlay);
	 document.getElementById("js-overlay").style.display = "block";

	 var selectedFeature;
	 var pointSelect = new ol.interaction.Select({
	 	condition: ol.events.condition.click,
	 	layers: [pointVectorLayer]
	 });

	 map.addInteraction(pointSelect);

	 pointSelect.on('select', function(event) {
	 	selectedFeatureCoord = event.mapBrowserEvent.coordinate;
	 	selectedFeature = event.selected[0];
	 	console.log(selectedFeature);
	 	(selectedFeature) ?
	 		delOverlay.setPosition(selectedFeatureCoord) :
	 		delOverlay.setPosition(undefined);
	 });

	 document.getElementById('js-remove').addEventListener('click', function() {
    pointVectorLayer.getSource().removeFeature(selectedFeature);
    delOverlay.setPosition(undefined);
    pointSelect.getFeatures().clear();
});





	/*Array in which to store newly added points from file*/
	var pointCoords = [];	


	/*Function to allow the uploading of a file. If it is a latlong CSV, each coordinate pair is passed into an array, which is added to the pointCoords array
	* which will be processed outside of the function
	*/
	function readBlob(opt_startByte, opt_stopByte) {

	    var files = document.getElementById('files').files;
	    if (!files.length) {
	      alert('Please select a file!');
	      return;
	    }

	    var file = files[0];
	    var start = parseInt(opt_startByte) || 0;
	    var stop = parseInt(opt_stopByte) || file.size - 1;

	    var reader = new FileReader();

	    reader.onloadend = function(evt) {
	      if (evt.target.readyState == FileReader.DONE) { // DONE == 2
	        document.getElementById('byte_content').textContent = evt.target.result;
	        
	       /* Document is read as a string and separated into an array, which each new line being placed in a separate element*/
			var text = evt.target.result;	 
			var lines = text.split("\n");	

			/*Loop through each element of the lines array, and split each element at the comma within the element (ie. ["523, 234"] -> [523, 234]. Each new element is then parsed into a float.
			* This whole process converts the initial single string, to an array of strings, which are finally converted into further arrays, whose elements are parsed
			* into floats. These elements representing latlon are added to a new array (pointCoord), which are sequentially added to an array of point coordinates (pointCoords)*/
			for (var i=0; i<lines.length -1; i++){
					var element = lines[i].split(",");
					var latx = parseFloat(element[0]);
					var lony = parseFloat(element[1]);
					var pointCoord = [latx, lony];
					pointCoords.push(pointCoord);
			};
			
	      };

	    };



	    var blob = file.slice(start, stop + 1);
	    reader.readAsBinaryString(blob);
		
	  };

	  
	  
	  document.querySelector('.readBytesButtons').addEventListener('click', function(evt) {
	    if (evt.target.tagName.toLowerCase() == 'button') {
	      var startByte = evt.target.getAttribute('data-startbyte');
	      var endByte = evt.target.getAttribute('data-endbyte');
	      readBlob(startByte, endByte);
	    }
	  }, false);


	 /*Function to load points from file onto map*/
	 $("button#add-file-points").on('click', function() {
		window.alert("Click points and 'Remove' button to delete points");
		for (var j = 0; j < pointCoords.length; j++) {
			var latitude = pointCoords[j][0];
			var longitude = pointCoords[j][1];
		 	var point = new ol.geom.Point(pointCoords[j]);
			var featurePoint = new ol.Feature({
				name: "Point",
				geometry: point

			});
			pointVectorLayer.getSource().addFeature(featurePoint);


		 }

	});


	 



	/*Function to add points manually on click*/
	 $("button#add-points").on('click', function() {
		 window.alert("Double click on map to add points. Click points and 'Remove' button to delete points");
			

			map.on('dblclick', function(event) {
				
				var lat = event.coordinate[0];
				var lon = event.coordinate[1];
				
				var latLon = [lat, lon]
				var point = new ol.geom.Point(latLon);
				var featurePoint = new ol.Feature({
					name: "Point",
					geometry: point

				});
			pointVectorLayer.getSource().addFeature(featurePoint);


			});
		
		});



		$('#postPoints').click(function() {
			var time_travel = parseFloat($("#time_travel").val()); 
			if(time_travel.length == 0) {
				time_travel = 2;
			}
			var travel_method = $("#impedance_select").find("option:selected").attr("id");
			var country_chosen = country;
			var population_chosen = $("#raster_select").find("option:selected").attr("id"); 
			var features = pointVectorLayer.getSource().getFeatures();
	 		var pointsArray = [];
	 		features.forEach(function(feature){
	 			pointsArray.push(ol.proj.transform(feature.getGeometry().getCoordinates(), 'EPSG:3857', 'EPSG:4326'));
	 		});
	 		console.log(pointsArray);
	 		$.ajax({
	 			data: JSON.stringify({
	 				'array' : pointsArray, 
	 				'time_travel': time_travel,
	 				'travel_method': travel_method,
	 				'country_chosen': country_chosen,
	 				'population_chosen': population_chosen
	 			}),
	 			contentType: "application/json; charset=utf-8",
	 			type: 'POST',
	 			url: '/process',
	 			success: function(response) {
					console.log(JSON.parse(response));
				}
	 		})
	})

};