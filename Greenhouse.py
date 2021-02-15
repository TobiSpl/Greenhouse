"""
Written by Tobias Splith

Script running on a Raspberry Pi Zero in our Greenhouse 
"""

import RPi.GPIO as GPIO
import spidev
import time
import Adafruit_DHT
import datetime
from picamera import PiCamera

def getTemp(pin,sensor=Adafruit_DHT.DHT22):
    Temp,AHumi=None,None
    n=0
    #10 Leseversuche
    while (Temp==None or AHumi==None) and n<10:
        if n>0:
            print("retry ",n,"GPIO",pin)
            time.sleep(0.01)
        AHumi, Temp = Adafruit_DHT.read(sensor, pin)
        n+=1
        if n==10:
            return 0,0
    return Temp, AHumi

def getSHum(CH,spi):
    #Channel ist binär, Format 0b1***0000 -> umwandlung zu dezimalzahl:
    CHdez=(8+CH)*16
    antwortbytes = spi.xfer([1,CHdez,0]) 
    value= ((antwortbytes[1]*256) + antwortbytes[2])#byte 0 wird nicht benutzt
    pvalue= (863-value)/420*100
    #print(value,pvalue)
    return pvalue

def write2log(hour,minute,second,T,rH,SH,logfile):
    file=open(logfile,"a")
    T4log='\t'.join(map("{:.2f}".format,T))
    rH4log='\t'.join(map("{:.2f}".format,rH))
    SH4log='\t'.join(map("{:.2f}".format,SH))
    output=str(hour)+"\t"+str(minute)+"\t"+str(second)+"\t"+T4log+"\t"+rH4log+"\t"+SH4log+"\n"
    file.write(output)
    file.close()
    
def event2log(hour,minute,second,message,logfile):
    file=open(logfile,"a")
    output="#"+str(hour)+"\t"+str(minute)+"\t"+str(second)+"\t"+message+"\n"
    file.write(output)
    file.close()
    
def newlog(now):
    logfile="log_" + str(now.year) + "_" + str(now.month).zfill(2) + "_" + str(now.day).zfill(2) + ".log"
    message="Start"
    event2log(now.hour,now.minute,now.second,message,logfile)
    return logfile

def ADCset(i):   #ADC ansteuern
    spi=spidev.SpiDev()
    spi.open(0,i)
    spi.max_speed_hz=1000000
    return spi
    
def Mset(PINS):
    GPIO.setmode(GPIO.BCM)
    for PIN in PINS:
        GPIO.setup(PIN,GPIO.OUT)#

def MZero(PINS): #set all to low
    for PIN in PINS:
        GPIO.output(PIN,0)

def MRotate(PINS): #half revolution
    PPINS=PINS+[PINS[0]] #append last element to enable smooth movement
    for i in range(24*513): #513.024 =full revolution, 48 Zähne -> 24, 16 weil eine Seite gerade nicht weit genug aufgeht
        for j in range(len(PINS)):
            GPIO.output(PPINS[j+1],1) #set next to 1
            time.sleep(0.001)
            GPIO.output(PPINS[j],0) #set current to 0#
            time.sleep(0.001)
    MZero(PINS)
            
def MRotateCCW(PINS): #half revolution counterclockwise
    PPINS=PINS+[PINS[0]] #append last element to enable smooth movement
    for i in range(24*513): #513.024 =full revolution, 48 Zähne -> 24, 16 weil eine Seite gerade nicht weit genug aufgeht
        for j in range(len(PINS),0,-1): #count down
            GPIO.output(PPINS[j-1],1) #set next to 1
            time.sleep(0.001)
            GPIO.output(PPINS[j],0) #set current to 0#
            time.sleep(0.001)
    MZero(PINS)
    
def Hatch_open(PINS):
    MRotateCCW(PINS)
    message='Hatch opened'
    event2log(now.hour,now.minute,now.second,message,logfile)
    return True #Hatch_is_open

def Hatch_close(PINS):
    MRotate(PINS)
    message='Hatch closed'
    event2log(now.hour,now.minute,now.second,message,logfile)
    return False #Hatch_is_open

def MOTION(PIR_PIN): #what happens if motion is detected
    now1=datetime.datetime.now()
    message='Motion Detected!'
    event2log(now1.hour,now1.minute,now1.second,message,logfile)
    take_Pictures(3,now1)
    time.sleep(1)
    
    
def take_Pictures(n,now1):
    camera.start_preview()
    for i in range(n):
        time.sleep(2)
        camera.capture('images/image'+ "_" + str(now1.year) + str(now1.month).zfill(2) + str(now1.day).zfill(2) + "_"+ str(now1.hour).zfill(2)+ str(now1.minute).zfill(2)+ str(now1.second).zfill(2) + "_" + str(i) +'.jpg')
    camera.stop_preview()
    time.sleep(1)

def Fan_on(FAN_GPIO):
    GPIO.output(FANS_GPIO, GPIO.HIGH)
    message='Fans on'
    event2log(now.hour,now.minute,now.second,message,logfile)
    return True #Fan_is_on
    
def Fan_off(FAN_GPIO):
    GPIO.output(FANS_GPIO, GPIO.LOW)
    message='Fans off'
    event2log(now.hour,now.minute,now.second,message,logfile)
    return False #Fan_is_on

GPIO.setmode(GPIO.BCM)
logfile=None
TPIN=[21,26,20] #GPIO PINS with Temperature/rH Sensors
T = [None] * len(TPIN)
rH= [None] * len(TPIN)
SHCH=[0,1,2] #channels of the ADC with Soil Humidity sensors
SH=[None] * len(SHCH)
###Motorkonfiguration
MPIN0=2
MPIN1=3
MPIN2=15
MPIN3=14
MPINS=[MPIN0,MPIN1,MPIN2,MPIN3]
###IR-MotionDetektor
IRPIN=16
GPIO.setup(IRPIN, GPIO.IN)
###Fan Relais Setup
FANS_GPIO=6
GPIO.setup(FANS_GPIO, GPIO.OUT)

###Turn everything on
spi=ADCset(0) #SPI Kanal (hier 0)
Mset(MPINS)
MZero(MPINS)
GPIO.output(FANS_GPIO, GPIO.LOW)
Fan_is_on=False
Hatch_is_open=False #Make sure hatch is closed when restarting
Camera_is_on=False
Tcounter_open,Tcounter_close=0,0

###lets start
now = datetime.datetime.now()
day=now.day
camera = PiCamera()
camera.resolution=(3280,2464)#(1640,922)
camera.iso=800
while True:
    #Timestamp
    now = datetime.datetime.now()
    #Logfile
    if logfile==None or day!=now.day:
        logfile=newlog(now)
    day=now.day #save day for next loop
    #Delay between Measurements
    delay=59.5
    #Aquire Data
    for n,PIN in enumerate(TPIN):
        T[n],rH[n]=getTemp(PIN)
    for n,CH in enumerate(SHCH):
        SH[n]=getSHum(CH,spi)#
    write2log(now.hour,now.minute,now.second,T,rH,SH,logfile)
    #Act
    #Camerastuff
    if now.hour>=22 and Camera_is_on==False:
        GPIO.add_event_detect(IRPIN, GPIO.RISING)
        GPIO.add_event_callback(IRPIN, MOTION)
        Camera_is_on=True
    if now.hour>=6 and now.hour<=17 and Camera_is_on==True:
        GPIO.remove_event_detect(IRPIN)
        Camera_is_on=False
        
    #Hatchstuff
    if Hatch_is_open==False and T[0]>32.0 and T[1]<T[0]:
        if Tcounter_open<3:
            Tcounter_open=Tcounter_open+1
        else:
            Hatch_is_open=Hatch_open(MPINS)
            Fan_is_on=Fan_on(FANS_GPIO)
            delay=0
            Tcounter_open=0
    else:
        Tcounter_open=0
    if Hatch_is_open==True and T[0]<28.0:
        if Tcounter_close<3:
            Tcounter_close=Tcounter_close+1
        else:
            Fan_is_on=Fan_off(FANS_GPIO)
            Hatch_is_open=Hatch_close(MPINS)
            delay=0
            Tcounter_close=0
    else:
        Tcounter_close=0
    #Wait
    time.sleep(delay)
    #Repeat
    

#def getSHumid(Pin,SHMAX):


