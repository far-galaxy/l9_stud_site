# -*- coding: utf-8 -*-
import json
import os
import logging
import logging.handlers

def loadJSON(name):
	path = f"{name}.json"
	if os.path.exists(path):
		with open(path, encoding='utf-8') as file:
			return json.load(file)
	
		
def saveJSON(name, dct):
	path = f"{name}.json"
	with open(path, "w", encoding='utf-8') as file:
		json.dump(dct, 
				  file, 
				  ensure_ascii=False,
				  indent="\t")
		
def initLogger(logger):
	if not os.path.isdir(f'logs'):
		os.makedirs(f'logs') 

	f_handler = logging.handlers.TimedRotatingFileHandler('./logs/log', 
	                                                      when='midnight', 
	                                                      #atTime=datetime.time(11,25), 
	                                                      encoding="utf-8")

	f_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
	                             datefmt='%d-%b-%y %H:%M:%S')
	f_handler.setFormatter(f_format)
	f_handler.setLevel(logging.INFO)
	logger.addHandler(f_handler)

	c_handler = logging.StreamHandler()
	c_format = logging.Formatter('%(levelname)s : %(message)s')
	c_handler.setFormatter(c_format)
	logger.addHandler(c_handler)
	logger.setLevel(logging.DEBUG)	