#!/usr/bin/python
# -*- coding: utf-8 -*-
# Connect to Oregon Scientific BLE Weather Station
# Copyright (c) 2016 Arnaud Balmelle
#
# This script will connect to Oregon Scientific BLE Weather Station
# and retrieve the temperature of the base and sensors attached to it.
# If no mac-address is passed as argument, it will scan for an Oregon Scientific BLE Weather Station.
#
# Supported Oregon Scientific Weather Station: BA228
#
# Usage: python bleWeatherStation.py [mac-address]
#
# Dependencies:
# - Bluetooth 4.1 and bluez installed
# - bluepy library (https://github.com/IanHarvey/bluepy)
#
# License: Released under an MIT license: http://opensource.org/licenses/MIT
# Origin: https://www.instructables.com/id/Connect-Raspberry-Pi-to-Oregon-Scientific-BLE-Weat/

import logging
import time
import sqlite3
from bluepy.btle import * 

# uncomment the following line to get debug information
logging.basicConfig(format='%(asctime)s: %(message)s', level=logging.DEBUG)

WEATHERSTATION_NAME = "IDTBA228"

class WeatherStation:
        def __init__(self, mac):
                try:
                        self.p = Peripheral(mac, ADDR_TYPE_RANDOM)
                        self.p.setDelegate(NotificationDelegate())
                        logging.debug('WeatherStation connected !')
                except BTLEException:
                        self.p = 0
                        logging.debug('Connection to WeatherStation failed !')
                        raise

        def _enableNotification(self):
                try:
                        # Enable all notification or indication
                        self.p.writeCharacteristic(0x000c, b'\x02\x00')
                        self.p.writeCharacteristic(0x000f, b'\x02\x00')
                        self.p.writeCharacteristic(0x0012, b'\x02\x00')
                        self.p.writeCharacteristic(0x0015, b'\x02\x00')
                        self.p.writeCharacteristic(0x0018, b'\x01\x00')
                        logging.debug('Notifications enabled')

                except BTLEException as err:
                        logging.debug('Error')
                        print(err)
                        self.p.disconnect()

        def monitorWeatherStation(self):
                try:
                        # Enable notification
                        self._enableNotification()
                        # Wait for notifications
                        while self.p.waitForNotifications(6000.0):
                                # handleNotification() was called
                                continue
                        logging.debug('Notification timeout')
                except:
                        return None

                return True

        def disconnect(self):
                self.p.disconnect()

class NotificationDelegate(DefaultDelegate):
        def __init__(self):
                DefaultDelegate.__init__(self)
                self._indoor_type0 = None
                self._data = {}

        def handleNotification(self, cHandle, data):
                logging.debug('Notification received')
                formatedData = binascii.b2a_hex(data)
                if cHandle == 0x0014:
                        self._indoor_type0 = formatedData
                        logging.debug('indoor_type0 = %s', formatedData)
                        regs = self.getData()
                        if regs is not None:                        
                                #logging.debug(regs['data_type0'][8:10] + regs['data_type0'][6:8])
                                self._data['index0_temperature'] = regs['data_type0'][8:10] + regs['data_type0'][6:8]
                                self._data['index0_humidity'] = regs['data_type0'][12:14]
                                self._data['index0_pressure'] = regs['data_type0'][18:20] + regs['data_type0'][16:18]
                        self.displayData()
                else:
                        # skip other indications/notifications
                        logging.debug('handle %x = %s', cHandle, formatedData)

        def getData(self):
                if self._indoor_type0 is not None:
                        # return sensors data
                        return {'data_type0':self._indoor_type0}
                else:
                        return None

        def getValue(self, indexstr):
                val = int(self._data[indexstr], 16)
                return val

        def displayData(self):
                temp = self.getValue('index0_temperature') / 10.0
                logging.debug('Indoor temp : %.1f°C', temp)
                hum = self.getValue('index0_humidity') 
                logging.debug('Indoor humidity : %.1f%%', hum)
                press = self.getValue('index0_pressure') / 10.0
                logging.debug('Indoor pressure : %.1fhPa', press)
                return None

class ScanDelegate(DefaultDelegate):
        def __init__(self):
                DefaultDelegate.__init__(self)

        def handleDiscovery(self, dev, isNewDev, isNewData):
                global weatherStationMacAddr
                if dev.getValueText(9) == WEATHERSTATION_NAME:
                        # Weather Station in range, saving Mac address for future connection
                        logging.debug('WeatherStation found')
                        weatherStationMacAddr = dev.addr

if __name__=="__main__":

        weatherStationMacAddr = None

        if len(sys.argv) < 2:
                # No MAC address passed as argument
                try:
                        # Scanning to see if Weather Station in range
                        scanner = Scanner().withDelegate(ScanDelegate())
                        devices = scanner.scan(2.0)
                except BTLEException as err:
                        print(err)
                        print('Scanning required root privilege, so do not forget to run the script with sudo.')
        else:
                # Weather Station MAC address passed as argument, will attempt to connect with this address
                weatherStationMacAddr = sys.argv[1]

        if weatherStationMacAddr is None:
                logging.debug('No WeatherStation in range !')
        else:
                try:
                        # Attempting to connect to device with MAC address "weatherStationMacAddr"
                        weatherStation = WeatherStation(weatherStationMacAddr)

                        if weatherStation.monitorWeatherStation() is not None:
                                # WeatherStation data received
                                logging.debug('Data were received from WeatherStation')
                        else:
                                logging.debug('No data received from WeatherStation')

                        weatherStation.disconnect()

                except KeyboardInterrupt:
                        logging.debug('Program stopped by user')
