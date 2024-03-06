from pymodbus.client import ModbusSerialClient as ModbusClient
from pymodbus.exceptions import ModbusIOException
import time

# 연결할 시리얼 포트 및 Modbus 주소 설정
SERIAL_PORT = 'COM9'  # 적절한 시리얼 포트로 변경
MODBUS_ADDRESS = 2  # Modbus 장치의 주소

# 레지스터 주소 설정
READ_REGISTER = 1001
WRITE_REGISTER = 1002

READ_COIL = 2001
WRITE_COIL = 2002

# Modbus RTU 클라이언트 객체 생성
client = ModbusClient(method='rtu', port=SERIAL_PORT, timeout=1, stopbits=1, bytesize=8, parity='N', baudrate=19200)
connection = client.connect()

try:
    # 레지스터에 쓸 값
    write_value = 321

    # Modbus 장치에 쓰기
    print(f'Writing value {write_value} to register {WRITE_REGISTER}')
    client.write_register(WRITE_REGISTER, write_value, unit=MODBUS_ADDRESS)
    client.write_coil(2001, True, unit=MODBUS_ADDRESS)

    # Modbus 장치에서 읽기
    try:
        result = client.read_input_registers(READ_REGISTER, 1, unit=MODBUS_ADDRESS)
        result_1 = client.read_coils(2002, 1, unit=MODBUS_ADDRESS)
        print(result_1.bits[0])
        read_value = result.registers[0]
        print(f'Read value {read_value} from register {READ_REGISTER}')
    except ModbusIOException as e:
        print(f'Error reading value: {e}')

except KeyboardInterrupt:
    # 사용자가 프로그램을 중단하면 정리 작업 수행
    print('Program terminated by user')
finally:
    client.close()
