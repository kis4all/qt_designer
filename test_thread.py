from PySide6.QtCore import *
from PySide6.QtWidgets import *

import sys
import time

# 내 돈
balance = 100

# 돈을 1씩 계속 없애는 QThread
class Balance_decrease(QThread):
    # Custom Signal 생성
    UpdateBalance = Signal()

    # QThread의 주 함수
    def run(self):
        # 내 돈을 Global에서 가져온다.
        global balance
        # 무한 루프
        while True:
            # 내 돈을 1원씩 계속 없앤다
            balance -= 1
            # 없애고 난 돈을 Emit(이벤트 발생)한다.
            self.UpdateBalance.emit()
            # 1초 대기
            time.sleep(1)


# 메인 윈도우
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        # 내 돈 표출할 레이블 하나 추가
        self.lbl = QLabel(str(balance))

        # 쓰레드 호출 버튼
        self.btn1 = QPushButton("FIRE")
        # 버튼 선택 시 함수 연결
        self.btn1.clicked.connect(self.btn1_clicked)

        # UI 설정
        self.layout = QHBoxLayout()
        self.layout.addWidget(self.lbl)
        self.layout.addWidget(self.btn1)

        self.setLayout(self.layout)

    def btn1_clicked(self):
        try:
            # 쓰레드 클래스 선언
            x = Balance_decrease(self)
            # 내 돈에 대한 이벤트 호출 시 함수 연결
            x.UpdateBalance.connect(self.lbl_update)
            # 쓰레드 클래스 시작!
            x.start()

        except KeyboardInterrupt:
            print("KeyboardInterrupt")

    def lbl_update(self):
        # 내 돈 표출
        self.lbl.setText(str(balance))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    app.exec()
    