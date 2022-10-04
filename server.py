# -*- coding: utf-8 -*-
from libraries.utils import *
from flask import *

app = Flask(__name__)

@app.route("/") 
def index():
	return send_file("site/index.html")

@app.route('/media/<path:path>', methods=['GET'])
def get_media(path):
	try:
		return send_file(f"site/media/{path}")
	except FileNotFoundError:
		abort(404)
		
@app.route("/stuff") 
def stuff():
	page = request.args.get('page')
	if page == None:
		return send_file("stuff/index.html")
	else:
		return send_file("stuff/video.html")

@app.route('/files/<path:path>', methods=['GET'])
def stuff_files(path):
	try:
		return send_file("stuff/files/"+path)
	except FileNotFoundError:
		abort(404)		

if __name__ == "__main__":
	app.run(host='0.0.0.0')