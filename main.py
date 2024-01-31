import sys
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, QThread, Signal, QObject
import time

from pymodbus.client import ModbusSerialClient as ModbusClient
from pymodbus.exceptions import ModbusIOException

# 연결할 시리얼 포트 및 Modbus 주소 설정
SERIAL_PORT = 'COM9'  # 적절한 시리얼 포트로 변경
MODBUS_ADDRESS = 2  # Modbus 장치의 주소

# 레지스터 주소 설정
READ_REGISTER = 1001
WRITE_REGISTER = 1002

# Modbus RTU 클라이언트 객체 생성

#client = ModbusClient(method='rtu', port=SERIAL_PORT, timeout=1, stopbits=1, bytesize=8, parity='N', baudrate=19200)
#connection = client.connect()

# 전류값 읽기 통신포트 설정
import serial
serial_current = serial.Serial("COM7",
                               9600,
                               parity=serial.PARITY_NONE,
                               stopbits=serial.STOPBITS_ONE,
                               bytesize=serial.EIGHTBITS,
                               timeout=1)
    
from main_monitor import Ui_MainWindow


lan_adapter = '\\Device\\NPF_{2FD30230-9071-4D19-9F93-9FEB54B2AA23}'    # notebook
f1 = open("load.txt", 'r')
load_file = f1.readline()
f1.close

global modified_load
modified_load = int(load_file)

f2 = open("time.txt", 'r')
time_file = f2.readline()
f2.close

inspection_time = int(time_file)


import os
import threading
import time
import datetime

import tkinter as tk
import tkinter.font
from tkinter import Menu

import pysoem
import ctypes
import sys
import serial
from threading import Timer

l7nh = None
load_value = 0

inspection_on = False
inspection_check = False
result_final_rpm = 0
rpm_max = 2940
rpm_min = 1360
set_current_min = 1.0
set_current_man = 7.0
current_ng = False

inspection_time_ns = (inspection_time - 5) * 100000000
inspection_endtime_ns = (inspection_time + 20) * 100000000

class InputPdo(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('statusword', ctypes.c_uint16),
        ('valocity_actual_value', ctypes.c_int32),
        ('torque_actual_value', ctypes.c_int16),
        ('touch_probe_status', ctypes.c_uint16),
        ('touch_probe_1_positive_edge_position_value', ctypes.c_int32),
        ('digital_Inputs', ctypes.c_uint32),
    ]


class OutputPdo(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('controlword', ctypes.c_int16),
        ('target_velocity', ctypes.c_int32),
        ('target_torque', ctypes.c_int16),
        ('digital_outputs', ctypes.c_uint32),
    ]

modes_of_operation = {
    'No mode': 0,
    'Profile position mode': 1,
    'Profile velocity mode': 3,
    'Profile torque mode':4,
    'Homing mode': 6,
    'Cyclic synchronous position mode': 8,
    'Cyclic synchronous velocity mode': 9,
    'Cyclic synchronous torque mode': 10,
}

def convert_input_data(data):
    return InputPdo.from_buffer_copy(data)

def l7nh_config_func(slave_pos):
    l7nh.sdo_write(0x1601, 2, bytes(ctypes.c_uint32(0x60FF0020)))
    l7nh.sdo_write(0x1601, 3, bytes(ctypes.c_uint32(0x60710010)))
    #l7nh.sdo_write(0x1601, 4, bytes(ctypes.c_uint32(0x60FE0120)))
    l7nh.sdo_write(0x1A01, 2, bytes(ctypes.c_uint32(0x606C0020)))
    l7nh.sdo_write(0x1A01, 3, bytes(ctypes.c_uint32(0x60770010)))

class Inspection(QObject):
    inspection_finished = Signal()
    inspection_rpm = Signal(int)
    final_rpm = Signal(int)

    def __init__(self):
        super().__init__()

    def run(self):
        #print("Inspection function")
        
        global l7nh
        global actual_velocity
        global start_signal
        global inspection_on
        global result_final_rpm
        global load_value
        global modified_load
    
        time_check_1 = 0
        time_check_2 = 0
        result_final = 2150
        
        master = pysoem.Master()
    
        master.open(lan_adapter)
        if master.config_init() > 0:
            l7nh = master.slaves[0]
            l7nh.config_func = l7nh_config_func
            
            master.config_map()
            if master.state_check(pysoem.SAFEOP_STATE, 50_000) == pysoem.SAFEOP_STATE:
                master.state = pysoem.OP_STATE
                master.send_processdata()
                master.receive_processdata(1_000)
                master.write_state()
                
                if master.state_check(pysoem.OP_STATE, 5_000_000) == pysoem.OP_STATE:
                    output_data = OutputPdo()

                    # 모드설정 4 : 프로파일 토크 모드
                    l7nh.sdo_write(0x6060, 0, bytes(ctypes.c_int8(10)))
                    
                    for control_cmd in [6, 7, 15]:
                        output_data.controlword = control_cmd
                        output_data.target_torque = load_value
                        l7nh.output = bytes(output_data)
                        master.send_processdata()
                        master.receive_processdata(2_000)
                        time.sleep(0.03)
                    
                    try:
                        while 1:
                            l7nh.output = bytes(output_data)
                            master.send_processdata()
                            master.receive_processdata(1_000)

                            status_word = convert_input_data(l7nh.input).statusword

                            if status_word == 17975 :
                                #print(1)
                                machine_ng = 0
                            else :
                                #print(2)
                                machine_ng = 1
                            
                            load_value = modified_load
                            output_data.target_torque = load_value
                            
                            if inspection_on == True :
                                load_value = modified_load
                            else :
                                load_value = 0
                                           
                            actual_velocity = int(convert_input_data(l7nh.input).valocity_actual_value / 262144 * 60)
                            self.inspection_rpm.emit(actual_velocity)
                            
                            if (inspection_check == True) and (inspection_check_done == False) :
                                result_final_rpm = actual_velocity
                                self.final_rpm.emit(result_final_rpm)
                                inspection_check_done = True
                                break
                            time.sleep(0.02)
                            
                    except KeyboardInterrupt:
                        print('stopped')
                    # zero everything
                    l7nh.output = bytes(len(l7nh.output))
                    master.send_processdata()
                    master.receive_processdata(1_000)
                else:
                    print('failed to got to op state')
            else:
                print('failed to got to safeop state')
            master.state = pysoem.PREOP_STATE
            master.write_state()
        else:
            print('no device found')
        master.close()
        self.inspection_finished.emit()

class Read_PLC(QObject):
    io_finished = Signal()
    io_progress = Signal(int)

    def __init__(self):
        super().__init__()

    def run(self):
        print("Read_PLC_run")
        
        while True:
            read_plc = client.read_coils(1001, 3, unit=MODBUS_ADDRESS)
            plc_ready = read_plc.bits[0]
            inspection_start = read_plc.bits[1]
            inspection_check = read_plc.bits[2]
            if plc_ready == 1 :
                print("plc_ready")
                self.io_progress.emit(1)
                if inspection_start == True :
                    print("inspection_start")
                    self.io_progress.emit(2)
                    break
                if inspection_check == True :
                    print("inspection_check")
                    self.io_progress.emit(3)
                    break
            time.sleep(0.1)

class Read_Current(QObject):
    current_finished = Signal()
    current_progress = Signal(str)
    
    global modified_load
    
    def __init__(self):
        super().__init__()

    def run(self):
        #print("Read_Current_run")
        try:
            while True:
                message_to_send = "$00R\r"
                serial_current.write(message_to_send.encode('utf-8'))
                #print(f"Sent: {message_to_send}")
                received_data = serial_current.read(100).decode('utf-8')
                #print(f"Received: {received_data}")
                
                self.current_progress.emit(received_data)
                time.sleep(0.02)
        finally:
            serial_current.close()
            
                
class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.pushButton.clicked.connect(self.load_save)
        self.lineEdit_load.returnPressed.connect(self.load_update)
        global modified_load
        self.lineEdit_load.setText(str(modified_load))
        
        #print("print_init")
        self.start_rpm()
        #self.start_Read_PLC()
        self.start_Read_Current()
        
    def start_Read_PLC(self):
        #print("start Read_PLC task")
        self.io_thread = QThread()
        self.io = Read_PLC()
        self.io.moveToThread(self.io_thread)
        
        self.io_thread.started.connect(self.io.run)
        self.io.io_finished.connect(self.io_thread.quit)
        self.io.io_finished.connect(self.io.deleteLater)
        self.io_thread.finished.connect(self.io_thread.deleteLater)
        self.io.io_progress.connect(self.read_plc_io_update)
        
        # Start the thread
        self.io_thread.start()
        
    def start_Read_Current(self):
        #print("start Read_Current task")
        self.current_thread = QThread()
        self.current = Read_Current()
        self.current.moveToThread(self.current_thread)
        
        self.current_thread.started.connect(self.current.run)
        self.current.current_finished.connect(self.current_thread.quit)
        self.current.current_finished.connect(self.current.deleteLater)
        self.current_thread.finished.connect(self.current_thread.deleteLater)
        self.current.current_progress.connect(self.read_current_update)
        
        # Start the thread
        self.current_thread.start()
        
        
    def start_rpm(self):
        #print("print_task")
        self.inspection_thread = QThread()
        self.inspection = Inspection()
        
        # Move the worker object to the thread
        self.inspection.moveToThread(self.inspection_thread)
        
        # Connect signals and slots
        self.inspection_thread.started.connect(self.inspection.run)
        self.inspection.inspection_finished.connect(self.inspection_thread.quit)
        self.inspection.inspection_finished.connect(self.inspection.deleteLater)
        self.inspection_thread.finished.connect(self.inspection_thread.deleteLater)
        self.inspection.inspection_rpm.connect(self.read_rpm_update)
        self.inspection.final_rpm.connect(self.final_rpm_update)
        
        # Start the thread
        self.inspection_thread.start()
        
    def read_rpm_update(self, value):
        #self.label.setText(f'Progress: {value}%')
        #print(f'Progress: {value}%')
        self.current_rpm.setText(f'{value}')
        
    def read_plc_io_update(self, value):
        print("print_read_plc_io_update")
        print(f'{value}')
        if value == 2:
            inspection_on = 1
        else :
            inspection_on = 0
            
        if value == 3:
            inspectin_check = 1
        else :
            inspectin_check = 0
 
    def read_current_update(self, response):
        #print("print_read_current_update")
        #print(f'{response}')
        current_value = response[15:20]
        voltage_value = response[9:14]
        self.label_current.setText(f'{current_value}')
        self.label_voltage.setText(f'{voltage_value}')

    def load_update(self):
        global modified_load
        modified_load = int(self.lineEdit_load.text())
        #print(modified_load)
        
    def load_save(self):
        global modified_load
        modified_load = int(self.lineEdit_load.text())
        f1 = open("load.txt", 'w')
        load_file = f1.write(self.lineEdit_load.text())
        f1.close
        

    def final_rpm_update(self, final_rpm ):
        self.label_final_rpm.setText(f'{final_rpm}')     
                   
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
