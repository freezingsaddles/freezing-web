from bs4 import BeautifulSoup
import datetime
from flask import render_template, make_response, request
from time import strptime, mktime
import sys

def update_file(infile, newdate, newtime):
	f = BeautifulSoup(infile)
	newdatetime = datetime.datetime.combine(newdate, newtime)
	t = f.metadata.time.get_text()
	mytime = datetime.datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ")
	offset = mytime - newdatetime #datetime.datetime.now()
	for x in f.find_all("time"):
		xtime = datetime.datetime.strptime(x.get_text(), "%Y-%m-%dT%H:%M:%SZ")
		xtime -= offset
		x.string = xtime.strftime("%Y-%m-%dT%H:%M:%SZ")
	return str(f)

def utils_upload_file():
	if request.method == 'POST':
		errors = {}
		f = request.files['fileInput']
		d = request.form['rideDate']
		try:
			newdate = datetime.datetime.strptime(d, "%m/%d/%Y")
		except:
			errors['date'] = "Could not parse date"
			newdate = None
		t = request.form['rideTime']
		try:
			ts = strptime(t, "%H:%M%p")
			newtime = datetime.time(ts.tm_hour, ts.tm_min)
		except:
			errors['time'] =  "Could not parse time"
			newtime = None
		if f:
			if newdate and newtime: 
				response = make_response(update_file(f, newdate, newtime))
				response.headers["Content-Disposition"] = "attachment; filename=newride.gpx"
				return response
		else:
			errors['file'] = "Invalid file"
		return render_template('fileutils/upload.html', errors=errors)
	else:
		return render_template('fileutils/upload.html')
