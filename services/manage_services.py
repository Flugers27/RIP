import subprocess
import os

# Указание путей к скриптам
command_service_1 = 'python C:\\Users\\Father\\Documents\\RIP-1\\services\\auth_service\\src\\auth_service.py'
command_service_2 = 'python C:\\Users\\Father\\Documents\\RIP-1\\services\\memory_page_service\\src\\memory_page_service.py'

def run_service_in_new_terminal(command):
    # Открыть новый терминал и выполнить команду
    subprocess.Popen(['start', 'cmd', '/K', command], shell=True)

# Запуск сервисов в новых терминалах
run_service_in_new_terminal(command_service_1)
run_service_in_new_terminal(command_service_2)
