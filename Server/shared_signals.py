from PyQt5.QtCore import QObject, pyqtSignal

class LogSignal(QObject):
    new_log = pyqtSignal(str)

log_signal = LogSignal()