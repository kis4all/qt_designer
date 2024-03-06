# 설정값 load.txt에서 역부하율 입력, time.txt에 측정시간 입력
# 측정시간은 PLC 설정값보다 0.5초 정도 길게 해야함

#lan_adapter = '\\Device\\NPF_{2FD30230-9071-4D19-9F93-9FEB54B2AA23}'    # notebook
lan_adapter = '\\Device\\NPF_{4E76B0F2-7C92-40D1-BC33-B7ADACF601D6}'    # side pc

# 파일에서
# 설정값 읽어오기
f1 = open("load.txt", 'r')
load_file = f1.readline()
f1.close

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

inspection_on = 0
result_final = 0
rpm_max = 2940
rpm_min = 1360
current_min = 1.0
current_min = 7.0
current_ng = 0

inspection_time_ns = (inspection_time - 5) * 100000000
inspection_endtime_ns = (inspection_time + 20) * 100000000

# notebook comport COM7
ser = serial.Serial(
    port='COM3',\
    baudrate=9600,\
    parity=serial.PARITY_NONE,\
    stopbits=serial.STOPBITS_ONE,\
    bytesize=serial.EIGHTBITS,\
        timeout=0)

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

def main_inspection():
    global l7nh
    global actual_velocity
    global widget_ready
    global widget_rpm
    global widget_rpm_result
    global widget_ok_ng
    global start_signal
    global inspection_on
    global result_final
    global load_value
    
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

            '''
            print('al status code {} ({})'.format(hex(l7nh.al_status),\
                                                  pysoem.al_status_code_to_string(l7nh.al_status)))
            '''

            if master.state_check(pysoem.OP_STATE, 5_000_000) == pysoem.OP_STATE:
                #print('OP_STATE')
                #print('The device is ready')

                output_data = OutputPdo()

                # 모드설정 4 : 프로파일 토크 모드
                l7nh.sdo_write(0x6060, 0, bytes(ctypes.c_int8(4)))
                """
                modes_of_operation = {
                'No mode': 0,
                'Profile position mode': 1,
                'Profile velocity mode': 3,
                'Profile torque mode':4,
                'Homing mode': 6,
                'Cyclic synchronous position mode': 8,
                'Cyclic synchronous velocity mode': 9,
                'Cyclic synchronous torque mode': 10,

                #l7nh.sdo_write(0x60FF, 0, bytes(ctypes.c_int32(3000000)))   # 프로파일 속도모드 속도설정 1000rpm
                #l7nh.sdo_write(0x6087, 0, bytes(ctypes.c_uint32(1000)))     # 프로파일 토크모드 토크기울기설정 1000
                #l7nh.sdo_write(0x6071, 0, bytes(ctypes.c_int16(375)))        # 프로파일 토크모드 토크설정 50 %
                # 부하1 0.09 Nm 28.125% 281  부하2 0.12Nm 37.5% 375
                #output_data.digital_outputs = 0x10000
                #l7nh.sdo_write(0x60FE, 1, bytes(ctypes.c_uint32(0x10000)))
                """
                                                   
                for control_cmd in [6, 7, 15]:
                    output_data.controlword = control_cmd
                    output_data.target_torque = load_value
                    l7nh.output = bytes(output_data)
                    master.send_processdata()
                    master.receive_processdata(2_000)
                    time.sleep(0.03)

                l7nh.sdo_write(0x60FE, 1, bytes(ctypes.c_uint32(0x20000)))
                # ready 신호 출력
                #time.sleep(0.1)
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
                        if machine_ng == 1 :
                            widget_ready.config(text="검사장비 이상", foreground='red')
                        if machine_ng == 0:
                            widget_ready.config(text="검사장비 정상", foreground='green')
                            

                        output_data.target_torque = load_value

                        if inspection_on == 1 :
                            load_value = modified_load
                        else :
                            load_value = 0
                                           
                        actual_velocity = int(convert_input_data(l7nh.input).valocity_actual_value / 262144 * 60)

                        widget_rpm.config(text=actual_velocity)
                        start_signal = convert_input_data(l7nh.input).digital_Inputs
                        
                        if inspection_on == 1 :
                            if (time_check_1 == 0) and (time_check_2 == 0) :
                                time_start = time.time_ns()
                                time_check_1 = 1
                                time_check_2 = 1
                                
                            time_elapse = time.time_ns()
                            time_interval = time_elapse - time_start
                            
                            if (time_interval > inspection_time_ns) and \
                               (time_check_1 == 1) :
                                result_final = actual_velocity
                                time_check_1 = 0
                                
                            if (time_interval > inspection_endtime_ns) and \
                               (time_check_1 == 0 and time_check_2 == 1) :
                                inspection_on = 0
                                time_check_2 = 0
                                
                        if (result_final > rpm_min and result_final < rpm_max) and \
                           current_ng == 0 :
                            l7nh.sdo_write(0x60FE, 1, bytes(ctypes.c_uint32(0x30000)))
                            widget_ok_ng.config(text="OK")
                            # OK 와 ready 신호 출력
                        else:
                            l7nh.sdo_write(0x60FE, 1, bytes(ctypes.c_uint32(0x20000)))
                            # ready 신호만 출력
                            widget_ok_ng.config(text="NG")
                            
                        widget_rpm_result.config(text=result_final)
                        #time.sleep(0.01)
                        
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

    
def monitor():
    global widget_rpm
    global widget_ready
    global widget_rpm_result
    global widget_ok_ng
    global load_value
    global result_final  
    global widget_current_result
    
    def program_end():
        ser.close()
        l7nh.sdo_write(0x60FE, 1, bytes(ctypes.c_uint32(0x0000)))
        main_window.destroy()
        main_window.quit()
        sys.exit()
        
    
    
    main_window = tk.Tk()
    main_window.title("대동모벨시스템")
    #main_window.geometry("800x700+10+10")    
    main_window.geometry("%dx%d+0+0" % (main_window.winfo_screenwidth(),main_window.winfo_screenheight()))
    main_window.attributes('-toolwindow', True) # 윈도우창 접기 버튼 없애기
    #main_window.attributes('-fullscreen', True)

    
    # Label
    font1=tkinter.font.Font(family="맑은 고딕", size=40)
    widget1 = tk.Label(main_window, text="모터 성능 검사 모니터", font=font1, foreground='blue')
    widget1.place(x=100, y=10)

    # 프로그램 종료 버튼
    font_end = tkinter.font.Font(family="맑은 고딕", size=15)
    button_end = tkinter.Button(main_window, text='프로그램 종료', overrelief="solid", \
                                    width=15, command=program_end, font=font_end)
    button_end.place(x=30, y=100)
    
    # 설비 ready
    font_ready = tkinter.font.Font(family="맑은 고딕", size=20)
    widget_ready = tk.Label(main_window, text="검사장비 정상", font=font_ready, foreground='green')
    widget_ready.place(x=230, y=100)

    # 프로그램 재시작 버튼
    font_restart = tkinter.font.Font(family="맑은 고딕", size=15)
    button_restart = tkinter.Button(main_window, text='프로그램 재시작', overrelief="solid", \
                                    width=15, command=restart_program, font=font_restart)
    button_restart.place(x=430, y=100)
  

    # Label
    font3=tkinter.font.Font(family="맑은 고딕", size=25)
    widget5 = tk.Label(main_window, text="정격검사 RPM", font=font3)
    widget5.place(x=200, y=200)

    # RPM 표시
    font5=tkinter.font.Font(family="맑은 고딕", size=80)
    widget_rpm = tk.Label(main_window, text="0000", font=font5, foreground='red')
    widget_rpm.place(x=120, y=250)

    # Label
    font6=tkinter.font.Font(family="맑은 고딕", size=50)
    widget7 = tk.Label(main_window, text="RPM", font=font6)
    widget7.place(x=400, y=280)

    # spec 표시
    font_spec=tkinter.font.Font(family="맑은 고딕", size=20)
    widget_spec = tk.Label(main_window, text="( SPEC : 1260 RPM  ~  2940 RPM )", font=font_spec)
    widget_spec.place(x=70, y=390)
    
    # 결과 RPM
    font_rpm=tkinter.font.Font(family="맑은 고딕", size=30)
    widget12 = tk.Label(main_window, text="측정회전수(RPM):", font=font_rpm)
    widget12.place(x=50, y=430)

    # 최종 결과 RPM 표시
    widget_rpm_result = tk.Label(main_window, text="0", font=font_rpm)
    widget_rpm_result.place(x=400, y=430)

    # 측정 전류
    font_current=tkinter.font.Font(family="맑은 고딕", size=30)
    widget_current_title = tk.Label(main_window, text="측정전류(A):", font=font_current)
    widget_current_title.place(x=145, y=480)

    # 측정 전류 표시
    widget_current_result = tk.Label(main_window, text="3.5", font=font_current)
    widget_current_result.place(x=400, y=480)

    # Label
    font14=tkinter.font.Font(family="맑은 고딕", size=40)
    widget14 = tk.Label(main_window, text="종합판정:", font=font14)
    widget14.place(x=50, y=550)

    # Label
    font15=tkinter.font.Font(family="맑은 고딕", size=40)
    widget_ok_ng = tk.Label(main_window, text="OK", font=font15, foreground='red')
    widget_ok_ng.place(x=400, y=550)


    """
    메뉴바 = Menu(main_window)
    main_window.config(menu=메뉴바)
    파일 = Menu(master=메뉴바, tearoff=False)
    메뉴바.add_cascade(label="파일", menu=파일)
    파일.add_command(label="종료", command=program_end)
    """
    
    main_window.protocol('WM_DELETE_WINDOW', program_end)
    main_window.mainloop()
    
def start_signal_check():
    global start_signal
    global inspection_on

    while 1:
        try:
            delay_current = (inspection_time - 5) / 10
            delay_save = (inspection_time + 30) / 10

            time.sleep(0.01)           
            if (inspection_on == 0) and (start_signal == 0b10000000000000000):
                inspection_on = 1
                Timer(delay_current, current_check).start()
                Timer(delay_save, data_save).start()

        except KeyboardInterrupt:
            print('stopped')
            break
               
def current_check():
    global widget_current_result
    #global current_ng
    global inspection_on
    
    ser.write(b'\x01\x03\x00\x32\x00\x02\x65\xC4')
    time.sleep(0.1)
    response = ser.readline()
    current_value = (response[3]*16777216 + response[4]*65536 \
                    + response[5]*256 + response[6]) / 10000
    
    widget_current_result.config(text=current_value)
    
    if (current_value > current_min) and (current_value < current_max) :
        current_ng = 0
    else:
        current_ng = 1

                        
def restart_program():
    ser.close()
    python = sys.executable
    os.execl(python, python, * sys.argv)


def data_save():
    
    now = datetime.datetime.now()
    now_date = now.strftime('%Y_%m_%d')
    now_time = now.strftime('%H:%M:%S')
    file_name = 'data\\' + now_date + '.txt'
    
    if not os.path.exists(file_name) :
        file_object = open(file_name, 'w+')
        line_num = 1
    else :
        with open(file_name, "r") as file_object:
            file_lines = file_object.readlines()
            line_num = int(file_lines[-1][0:4]) + 1
    
    file_object.close()
    file_object = open(file_name, 'a')
    
    num = str(line_num).zfill(4) + '\t'
    rpm = str(widget_rpm_result['text'])+ '\t'
    current = str(widget_current_result['text']) + '\t'
    ok_ng = str(widget_ok_ng['text']) + '\t'

    write_data = num + rpm + current + ok_ng + now_time + '\n'
    file_object.write(write_data)
    file_object.close()


# 쓰레드 생성
t_monitor = threading.Thread(target=monitor)
t_monitor.deamon = True
t_inspection = threading.Thread(target=main_inspection)
t_inspection.deamon = True
t_signal = threading.Thread(target=start_signal_check)
t_signal.deamon = True


# 쓰레드 시작
t_monitor.start()
time.sleep(0.5)
t_inspection.start()
time.sleep(0.5)
t_signal.start()





