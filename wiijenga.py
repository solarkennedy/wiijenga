#!/usr/bin/python
"""
WiiJenga
Kyle Anderson
GPL
Derived from http://abstrakraft.org/cwiid/ticket/63 by TBBle
"""


try:
	import pygame
except:
	print "Sorry, I can't seem to import pygame for some reason."
	print "Please check that the python-pygame package is installed, or get the latest version of pygame from http://www.pygame.org/"
	sys.exit(1)
	
try:
	import cwiid
except:
	print "Sorry, I can't seem to import cwiid for some reason."
	print "Please check that it and it's python bindings are installed, and also the balance board patch from:"
	print "http://abstrakraft.org/cwiid/ticket/63"
	sys.exit(1)

import sys
import os, math, random
import time as ptime
from pygame.locals import *
from ConfigParser import ConfigParser
from threading import Thread
import numpy

system_file = "system.ini"
if not os.path.lexists(system_file):
	print "Problem: System configuration file (system.ini) doesn't exist."
	sys.exit(1)
sconf = ConfigParser()
sconf.read(system_file)

class WeightSprite(pygame.sprite.Sprite):
	"""This class describes a sprite containing the weight."""
	def __init__(self):
		pygame.sprite.Sprite.__init__(self)
		self.weight = 0.0
		self.update()
		
	def update(self):
		global screen_res, sys_font_weight_fgcolour, sys_font_weight, screen_res
		self.text = str(self.weight) + " Blocks"
		self.image = sys_font_weight.render(self.text, True, sys_font_weight_fgcolour)
		self.rect = self.image.get_rect()
		self.rect.bottomright = screen_res

def quit_app():
	pygame.quit()
	sys.exit(0)
	
def calcweight( readings, calibrations ):
	"""
	Determine the weight of the user on the board in hundredths of a kilogram
	"""
	weight = 0
	for sensor in ('right_top', 'right_bottom', 'left_top', 'left_bottom'):
		reading = readings[sensor]
		calibration = calibrations[sensor]
		#if reading < calibration[0]:
		#	print "Warning, %s reading below lower calibration value" % sensor
		if reading > calibration[2]:
			print "Warning, %s reading above upper calibration value" % sensor
		# 1700 appears to be the step the calibrations are against.
		# 17kg per sensor is 68kg, 1/2 of the advertised Japanese weight limit.
		if reading < calibration[1]:
			weight += 1700 * (reading - calibration[0]) / (calibration[1] - calibration[0])
		else:
			weight += 1700 * (reading - calibration[1]) / (calibration[2] - calibration[1]) + 1700

	return weight
	
def gsc(readings, pos):
	global named_calibration
	reading = readings[pos]
	calibration = named_calibration[pos]
	
	if reading < calibration[1]:
		return 1700 * (reading - calibration[0]) / (calibration[1] - calibration[0])
	else:
		return 1700 * (reading - calibration[1]) / (calibration[2] - calibration[1]) + 1700
	

class Sensor:
        def __init__(self, location):
		self.samples= 100
		self.location = location
		self.tarevalue = float(0)
		self.values = list(0 for x in range(self.samples))
		self.smoothvalues = list(0 for x in range(self.samples))
                self.update()

        def update(self):
		balancedata = wiimote.state['balance']
		self.values.pop()
		self.values.insert(0,float(gsc(balancedata,self.location)))
		#print "we have " + str(len(self.values)) + "values"
		self.smoothvalues = smoothListGaussian(self.values)
		self.weight=float( self.smoothvalues[self.samples/2] - self.tarevalue )

	def tare(self):
		tarearray = []
		for i in range(50):
			balancedata = wiimote.state['balance']
			tarearray.append(float(gsc(balancedata,self.location)))
			pygame.time.wait(10)	
		taresmoothvalues = smoothListGaussian(tarearray)
		for i in range(50):
			self.tarevalue += taresmoothvalues[i]
		self.tarevalue = self.tarevalue / 50


def smoothListGaussian(list,strippedXs=False,degree=50):  
	list = [list[0]]*(degree-1) + list + [list[-1]]*degree
	window=degree*2-1  
	weight=numpy.array([1.0]*window)  
	weightGauss=[]  
	for i in range(window):  
		i=i-degree+1  
		frac=i/float(window)  
		gauss=1/(numpy.exp((4*(frac))**2))  
		weightGauss.append(gauss)  
	weight=numpy.array(weightGauss)*weight  
	smoothed=[0.0]*(len(list)-window)  
	for i in range(len(smoothed)):  
		smoothed[i]=sum(numpy.array(list[i:i+window])*weight)/sum(weight)  
	return smoothed  


global wiimote
mac = sconf.get("wiimote", "mac")
if mac:
	print "Trying to connect to pre-stored MAC: " + mac + " ..."
	wiimote = cwiid.Wiimote(mac)
else:
	print "mac not stored in system.ini"
	print "Please press the red 'connect' button on the balance board, inside the battery compartment."
	print "Do not step on the balance board."
	wiimote = cwiid.Wiimote()

wiimote.rpt_mode = cwiid.RPT_BALANCE | cwiid.RPT_BTN
wiimote.request_status()


balance_calibration = wiimote.get_balance_cal()
named_calibration = { 'right_top': balance_calibration[0],
					  'right_bottom': balance_calibration[1],
					  'left_top': balance_calibration[2],
					  'left_bottom': balance_calibration[3],
					}

Sensors=[]
Sensors.append(Sensor('left_top'))
Sensors.append(Sensor('right_top'))
Sensors.append(Sensor('left_bottom'))
Sensors.append(Sensor('right_bottom'))




xdisplay = sconf.get("display", "xdisplay")
if len(xdisplay) > 1:
	# using alternate display.
	print "Attempting to use device", xdisplay, "instead of the default."
	os.putenv("DISPLAY", xdisplay)

pygame.init()

sys_font_weight = pygame.font.SysFont(sconf.get("font_weight", "face"), int(sconf.get("font_weight", "size")))

sys_font_weight.set_italic(False)
sys_font_weight.set_underline(False)

bgcolour = (0, 0, 0)
sys_font_weight_fgcolour = (255, 255, 255)
screen_res = (int(sconf.get("display", "width")), int(sconf.get("display", "height")))
refresh_delay = int(sconf.get("display", "refresh_delay"))

screen_options = 0
if int(sconf.get("display", "fullscreen")) >= 1 and len(xdisplay) <= 1:
	screen_options = screen_options | pygame.FULLSCREEN

if int(sconf.get("display", "double_buffers")) >= 1:
	screen_options = screen_options | pygame.DOUBLEBUF

if int(sconf.get("display", "hardware_surface")) >= 1:
	screen_options = screen_options | pygame.HWSURFACE

if int(sconf.get("display", "opengl")) >= 1:
	screen_options = screen_options | pygame.OPENGL

screen = pygame.display.set_mode(screen_res, screen_options)
pygame.display.set_caption("Wii Jenga")

weight_sprite = WeightSprite()
weight_sprite.weight = 0.00
frame = 0

font = pygame.font.SysFont(sconf.get("font_weight", "face"), 12)
text = font.render('F11: Tare      F12: Quit', True, (255,255, 255), (0, 0, 0))
textRect = text.get_rect()

led = cwiid.LED1_ON
wiimote.led = led

while True:
	for event in pygame.event.get():
		if event.type == KEYDOWN:
			if event.key == K_F12:
				quit_app()	
			elif event.key == K_F11:
				for i in range(4):
					Sensors[i].tare()
	
	readings = wiimote.state['balance']

	wiimote.request_status()
	frame = frame + 1
	if frame == 50:
		frame = 0
		weight = 0
		for i in range(10):
			for j in range(4):
				#weight += Sensors[j].values[i] - Sensors[j].tarevalue
				weight += Sensors[j].smoothvalues[i] - Sensors[j].tarevalue
		weight = weight / 40 / .39
		#weight = (calcweight(wiimote.state['balance'], named_calibration) / 100.0)
		#print "%.2fkg" % weight
		weight_sprite.weight = int(round(weight))
	
	try: 
		totalweight = float(Sensors[0].weight + Sensors[1].weight + Sensors[2].weight + Sensors[3].weight)
		x_balance = (float(Sensors[1].weight + Sensors[3].weight) - float(Sensors[0].weight + Sensors[2].weight)) / totalweight
		if x_balance > 1:
			x_balance = 1
		elif x_balance < -1:
			x_balance = -1
		y_balance = (float(Sensors[2].weight + Sensors[3].weight) - float(Sensors[0].weight + Sensors[1].weight)) / totalweight
		if y_balance > 1:
			y_balance = 1
		elif y_balance < -1:
			y_balance = -1
		#print "x: " + str(x_balance) + "    y: " + str(y_balance)

	except:
		x_balance = 1
		y_balance = 1
	
	for i in range(4):
		Sensors[i].update()
#		print "Sensor " + Sensors[i].location + " wight: " + str(Sensors[i].weight) + "     tare: " + str(Sensors[i].tarevalue)  

	screen.fill(bgcolour) # blank the screen.
	
	xmid = screen_res[0]/2
	ymid = screen_res[1]/2
	
	block = (.058) * screen_res[0]
	pygame.draw.line(screen, (0,0,255), (screen_res[0]/2,0), (screen_res[0]/2,screen_res[1]), 2)
	pygame.draw.line(screen, (255,0,255), (xmid+block/2,0), (xmid+block/2,screen_res[1]), 2)
	pygame.draw.line(screen, (255,0,255), (xmid-block/2,0), (xmid-block/2,screen_res[1]), 2)

	pygame.draw.line(screen, (0,0,255), (0,screen_res[1]/2), (screen_res[0],screen_res[1]/2), 2)
	pygame.draw.line(screen, (255,0,255), (0,ymid + block/2), (screen_res[0],ymid + block/2), 2)
	pygame.draw.line(screen, (255,0,255), (0,ymid - block/2), (screen_res[0],ymid - block/2), 2)

	pygame.draw.rect(screen, (255,255,255), (xmid - (block * .5), ymid - (block * .5) , block  ,  block ), 2)

	weight_sprite.update()
	
	screen.blit(weight_sprite.image, weight_sprite.rect)
	screen.blit(text, textRect)
	
	xpos = (x_balance * (screen_res[0]/2)) + (screen_res[0]/2)
	ypos = (y_balance * (screen_res[1]/2)) + (screen_res[1]/2)
	
	if xpos > (xmid + (block * 1.5)) or xpos < (xmid - (block * 1.5)) or ypos > ymid + (block * 1.5) or ypos < ymid - (block * 1.5):
			boxcolor=(255,0,0)
			led ^= cwiid.LED1_ON
			wiimote.led = led
	else:
			boxcolor=(0,124,255)
			led = cwiid.LED1_ON
			wiimote.led = cwiid.LED1_ON

	pygame.draw.rect(screen, boxcolor, (xmid - (block * 1.5), ymid - (block * 1.5) , block * 3 ,  block * 3), 2)

	#print "balance:", x_balance, y_balance
	#print "position:", xpos,ypos
	pygame.draw.circle(screen, (255,0,0), (int(xpos), int(ypos)), 5)
	pygame.display.flip()
	pygame.time.wait(refresh_delay)	


