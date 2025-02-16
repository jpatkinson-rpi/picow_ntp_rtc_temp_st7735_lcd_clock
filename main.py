#-------------------------------------------------------------------
# NTP Time Decoder for RPi PICO-W
#
# Decode NTP Time at 3am and save to RTC
#
# Display RTC Date & Time on ST7735 LCD 
#
# NTP format: https://en.wikipedia.org/wiki/Network_Time_Protocol
#
# Uses  DS18x20 'onewire' temperature sensor
# 
#-------------------------------------------------------------------

from machine import Pin
from machine import Timer, Pin
from time import sleep
from machine import I2C
from ST7735 import TFT
from sysfont import sysfont
from machine import SPI,Pin
import time
import math
import machine, onewire, ds18x20

import network

from machine import RTC

from wifissid import get_wifi_ssid, get_wifi_passphrase

from bsttimes import bst_start_times, bst_end_times
from bsttimes import bst_start_dates, bst_end_dates
from bsttimes import BST_START_YEAR, BST_NUM_YEARS

import utime as time
import usocket as socket
import ustruct as struct

DEBUG = False

BL = 13
DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9

# SSID & PASSPHRASE for Wi-Fi
ssid = get_wifi_ssid()
passphrase = get_wifi_passphrase()

daysofweek = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
months     = [ '-', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec' ]
timezone   = [ 'GMT', 'BST' ]

BST_OFFSET = 60 * 60 # British Summer Time 1 hour offset

# UK NTP Hosts
NTP_HOSTS = [ 'uk.pool.ntp.org', 'ntp2d.mcc.ac.uk', 'ntp2c.mcc.ac.uk','ntp.cis.strath.ac.uk' ]

# NTP uses an epoch of 1 January 1900. Unix uses an epoch of 1 January 1970. 
NTP_EPOCH_OFFSET = 2208988800

dst_flag = 0
wlan = network.WLAN(network.STA_IF)

#################################################
# connect to WLAN
#################################################
def wlan_connect( ssid, passphrase ):  
   global wlan
   wlan.active(True)
   if wlan.status() != 3:
      wlan.connect(ssid, passphrase)
      while wlan.status() != 3:
         pass
   if wlan.status() != 3:
      print("failed to connect to", ssid)
      retval = False
   else:
      status = wlan.ifconfig()
      ipaddress = status[0]
      print('connected to', ssid, ipaddress)
      retval = True
   return retval


#################################################
# disconnect from WLAN
#################################################
def wlan_disconnect():
   global wlan
   wlan.disconnect()
   wlan.active(False)


########################################################
# BST is last Sunday in March to last Sunday in October
# check current time with bst_start_times & bst_end_times
########################################################
def dst_check( unix_format_time, year ):
   global dst_flag
   if unix_format_time > bst_start_times[year-BST_START_YEAR] and unix_format_time < bst_end_times[year-BST_START_YEAR]:
      dst_flag = True
   else:
      dst_flag = False
   return dst_flag


#################################################
# get time from NTP Server
#################################################
def get_ntp_time():
   retval = False

   NTP_QUERY = bytearray(48)
   NTP_QUERY[0] = 0x1B
  
   addr = None
   host_index = 0
   while addr == None:
      # wait for valid NTP server
      sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      sock.settimeout(10)
      try:
         addr = socket.getaddrinfo(NTP_HOSTS[host_index], 123)[0][-1]
      except OSError as error:
         print("OSError", error, NTP_HOSTS[host_index])
         host_index += 1
         if host_index == len(NTP_HOSTS):
            host_index = 0
         sock.close()
    
   print( "connected to:", NTP_HOSTS[host_index], addr)

   rc = sock.sendto(NTP_QUERY, addr)
   ntp_msg = sock.recv(48)
   sock.close()
   
   #NTP time bytes 40-44 network unsigned long format
   ntp_time = struct.unpack("!L", ntp_msg[40:44])[0]
   return ntp_time


#######################################################################
# Get NTP time
# convert from NTP to Unix Epoch
# check DST
# store to RTC
#######################################################################
def set_rtc_time():
   status = False
   if wlan_connect( ssid, passphrase):
      ntp_format_time = get_ntp_time()
      unix_format_time = ntp_format_time - NTP_EPOCH_OFFSET
      unix_format_gmtime = time.gmtime( unix_format_time )

      # NTP returns UTC (GMT)
      # check for DST and adjust
      dst_check( unix_format_time, unix_format_gmtime[0] )
      if dst_flag == True:
         unix_format_time += BST_OFFSET
      unix_format_gmtime = time.gmtime( unix_format_time )
      print(unix_format_gmtime)

      # gmtime: year, month, mday, hour, minute, second, weekday, yearday
      year = unix_format_gmtime[0]
      month = unix_format_gmtime[1]
      dayofmonth = unix_format_gmtime[2]
      dayofweek = unix_format_gmtime[6] + 1
      hour = unix_format_gmtime[3]
      minute = unix_format_gmtime[4]
      seconds = unix_format_gmtime[5]

      # RTC datetime: year, month, mday, week_day, hours, minutes, seconds, 0
      rtc.datetime((year, month, dayofmonth, dayofweek, hour, minute, seconds, 0))   
      wlan_disconnect()
      status = True
   else:
      status = False
    
   return status

######################################################
# main program body
######################################################
if __name__ == "__main__":

   yesterday = 0
   first_display = True

   #initialise TFT LCD using SPI interface
   spi = SPI(1, baudrate=20000000, polarity=0, phase=0, sck=Pin(10), mosi=Pin(11), miso=None)
   tft=TFT(spi,8,12,9)
   tft.initr()
   tft.rgb(True)
   
   # clear display
   tft.rotation(0)
   tft.fill(TFT.BLACK)
   tft.fillrect( (1, 1),(tft.size()[0], tft.size()[1]), TFT.BLACK)

   # rotate for landscape display
   tft.rotation(1)
   tft.fillrect( (0, 0),(tft.size()[0], tft.size()[1]), TFT.BLACK)

   # initialise onewire interface
   ds_pin = machine.Pin(28)
   ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))

   # scan onewire bus for devices
   ds_devs = ds_sensor.scan()
   print('Found DS devices: ', ds_devs) 
   
   rtc = RTC()
   
   set_rtc_time()
   
   while True:

      t = rtc.datetime()
      #year, month, day, weekday, hours, minutes, seconds, subseconds)
      year = t[0]
      month = t[1]
      dayofmonth = t[2]
      dayofweek = t[3]
      hour = t[4]
      minute = t[5]
      seconds = t[6]
      if DEBUG == True:
         print( "----------------")
         print( hour, minute, seconds, timezone[ dst_flag ] )
         print( daysofweek[dayofweek], dayofmonth, months[month], year )
         print( "----------------")

      if seconds == 0 or first_display:
         first_display = False
         # initiate temperature reading
         ds_sensor.convert_temp()
         time.sleep_ms(750)
         # read temperature
         value = ds_sensor.read_temp( ds_devs[0] )
         valuestr = '{:.1f}°C'.format(value)
         valuestr = '{:>4}'.format(valuestr)
         tft.fill(TFT.BLACK)
         # display temperature
         tft.text((0, 80), str(valuestr), TFT.GREEN, sysfont, 5, nowrap=True)
         # display time
         tft.text((0, 10), "{:>02d}:{:>02d}".format(hour, minute), TFT.GREEN, sysfont, 6, nowrap=True)     

      # update RTC at 3am
      if dayofmonth != yesterday and hour == 3:
         set_rtc_time()
         yesterday = dayofmonth
          
      time.sleep(0.5)
