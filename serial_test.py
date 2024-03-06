import serial

def send_receive_serial(port, baud_rate, message):
    # 시리얼 포트 열기
    ser = serial.Serial(port, baud_rate,parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)

    try:
        # 메시지 전송
        ser.write(message.encode('utf-8'))
        print(f"Sent: {message}")

        # 시리얼에서 데이터 받기
        received_data = ser.read(100).decode('utf-8')
        print(f"Received: {received_data}")

    finally:
        # 시리얼 포트 닫기
        ser.close()

if __name__ == "__main__":
    # 포트, 비트레이트, 보낼 메시지 설정
    serial_port = "COM7"  # 실제 포트에 맞게 변경
    baud_rate = 9600
    message_to_send = "$00R\r"

    # 시리얼 통신 함수 호출
    send_receive_serial(serial_port, baud_rate, message_to_send)
