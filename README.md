# picow_ntp_rtc_temp_st7735_lcd_clock
PICO-W NTP RTC Temperature ST7735 LCD Clock


Use apps generate-bst-times.py to create bsttimes.py
    'python3 apps/generate-bst-times.py > bsttimes.py'

Enter Wi-Fi SSID & Passphrase details into wifissid.py

Upload ST7735.py, sysfont.py & main.py, bsttimes.py, wifissid.py to RPi PICO-W

DS18x20 'onewire' temperature sensor connects to PICO GPIO28

# BOOT SEQUENCE

1: Decoding valid NTP data and display Date/Time
![Alt text](https://github.com/jpatkinson-rpi/picow_ntp_rtc_temp_st7735_lcd_clock/blob/main/images/prototype-001.jpg?raw=true "Date/Time decoded") 
