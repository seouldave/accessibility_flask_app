from flask import Flask, render_template, jsonify, request
from travel_time_v2 import *


app = Flask(__name__)

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
	data = request.get_json()
	startCoord = data['array']
	num_hours = data['time_travel']
	travel_method = data['travel_method']
	country_chosen = data['country_chosen'][:3]
	if data['population_chosen'][1:5] == "preg":
		population_chosen = "preg"
	elif data['population_chosen'][1:5] == "wocb":
		population_chosen = "wocba"
	else:
		population_chosen = "bth"
	
	results = main(startCoord, num_hours, travel_method, country_chosen, population_chosen)
	return results

if __name__ ==  "__main__":
	app.run(host='0.0.0.0', port=5000, debug=True)
