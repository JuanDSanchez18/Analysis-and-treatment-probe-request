"""
Programa para primer ESP32 en Raspberry con puerto "/dev/ttyUSB0",
se inicia este programa al haber un reinicio en la Raspberry con el
comando "crontab -e" en la línea de comandos.

"""
# Modulos necesarios
import serial  # https://github.com/pyserial/pyserial
import pyrebase  # https://github.com/thisbejim/Pyrebase

import time
from datetime import date, datetime

# Conexión serial con el puerto y tasa de baud definida.
# Solo termina hasta haber conexión.
serialport = "/dev/ttyUSB0"
boardRate = 115200

canBreak = False
while not canBreak:
    try:
        ser = serial.Serial(serialport, boardRate, timeout=30)
        canBreak = True
    except KeyboardInterrupt:
        print("\n[+] Exiting...")
        exit()
    except:
        print("[!] Serial connection failed... Retrying...")
        time.sleep(2)
        continue

print("[+] Serial connected. Name: " + ser.name)

# Configuración de Firebase, conexión con base de datos en tiempo real.
config = {
    "apiKey": "AIzaSyDmuMezNODQFRpu-Qd7scaNNmqLXURZtjI ",
    "authDomain": "rapberry-stutm-a0c0e.firebaseapp.com",
    "databaseURL": "https://rapberry-stutm.firebaseio.com/",
    "storageBucket": "rapberry-stutm.appspot.com"
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()

#
today = date.today()
todaystr = "D_" + str(today.strftime("%Y-%m-%d"))

# Dirección y extensión de los archivos reporte a guardar.
path = "/home/pi/Desktop/stuTM/Reportes/"
#path = "Reportes/"
ext = " Calle45.txt"

# Arreglos definidos a usar.
maclist = []
timestartlist = []
timefinallist = []
timedurationlist = []
repetitivelist = []
userscount = 0


# Cuando una dirección mac ha sido captada minimo 2 veces, con diferencia
# de 25 segundos entre los paquetes.
# Envía a Firebase los tiempos de captura y guarda en reporte .txt
def more_times(mac, rssi, timecapture, timestr):
    position = maclist.index(mac)
    # print(position)

    lasttime = timefinallist[position]

    # Mirar duration entre la ultima guardada y esta
    lastdurationtime = datetime.combine(today, timecapture) - datetime.combine(today, lasttime)
    lastdurationtime = lastdurationtime.total_seconds()
    lastdurationtime = round(lastdurationtime)

    if lastdurationtime > 25:

        # print (mac)

        timefinallist[position] = timecapture
        repetitive = repetitivelist[position]

        repetitive += 1
        repetitivelist[position] = repetitive
        repetitivestr = str(repetitive)

        if repetitive == 1:

            starttime = str(timestartlist[position])
            timedurationlist[position] = lastdurationtime
            durationtime = lastdurationtime

            if durationtime > 180:
                data = {"Tiempo_inicial": starttime, "Tiempo_final": timestr, "Duración (s)": durationtime}

            else:
                data = {"Tiempo_inicial": starttime, "Tiempo_final": timestr}

            db.child(initialtime).child("M_" + mac).set(data)

            global userscount
            userscount += 1
            db.child(initialtime).update({"Usuarios": userscount})

        else:

            durationtime = timedurationlist[position] + lastdurationtime
            timedurationlist[position] = durationtime

            if durationtime > 180:
                data = {"Tiempo_final": timestr, "Duracíón (s)": durationtime}

            else:
                data = {"Tiempo_final": timestr}

            # Update Firebase
            db.child(initialtime).child("M_" + mac).update(data)

        lastdurationtime = str(lastdurationtime)
        durationtime = str(durationtime)

        # Guardar en archivo .txt
        f.write(timestr + ", ")
        f.write(mac + ", " + rssi + ", ")
        f.write(repetitivestr + ", " + lastdurationtime + ", " + durationtime + " \n")
        f.flush()


# Cuando dirección MAC es captada por primera vez, se añade los valores a los arreglos
# y se guarda en archivo.
def first_time(mac, rssi, timecapture, timestr):
    maclist.append(mac)
    timestartlist.append(timecapture)
    timefinallist.append(timecapture)
    timedurationlist.append(0)
    repetitivelist.append(0)

    # Guardar en archivo .txt
    f.write(timestr + ", ")
    f.write(mac + ", " + rssi + ", 0 \n")
    f.flush()


# Función lectura ESP32
# Formato paquete recibido desde la ESP32:
# SMAC= 90:63:3B:9E:2D:27, RSSI= -32
def read_esp32():
    start = time.time()
    end = time.time()

    mact = ""
    timemact = datetime.now().time()

    # Tiempo de reporte definido acá
    while (end - start) < 900:  # 15 minutos

        infocapture = ser.readline()
        infocapture = infocapture.decode("ascii")

        if not infocapture:
            continue

        mac = infocapture[infocapture.index("SMAC= ") + 6:infocapture.index(", RSSI")]
        timecapture = datetime.now().time()

        mactdurationtime = datetime.combine(today, timecapture) - datetime.combine(today, timemact)
        mactdurationtime = mactdurationtime.total_seconds()

        # Para obtener solo un valor de la rafaga recibida desde la ESP32, se guarda MAC
        # y se compara con siguiente MAC, si es la misma no se tiene en cuenta, a menos que
        # la diferencia entre los paquetes sea de 25 segundos.
        if mac != mact or mactdurationtime > 25:

            mact = mac
            timemact = timecapture
            # print(MACT)

            dir_mac = str(mac)
            rssi = infocapture[infocapture.index("RSSI= ") + 6:infocapture.index("\r\n")]

            timecapture = timecapture.replace(microsecond=0)
            timestr = str(timecapture)

            if dir_mac in maclist:
                more_times(dir_mac, rssi, timecapture, timestr)
            else:
                first_time(dir_mac, rssi, timecapture, timestr)

        end = time.time()


# Se define el tiempo de captura y se prepara el archivo .txt
try:
    while True:
        while today == date.today():
            capturetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            capturehour = "H_" + time.strftime("%H:%M:%S")

            filename = path + capturetime + ext
            f = open(filename, 'w')
            f.write("Tiempo, SMAC, RSSI(dBm), Repetición, DuraciónA(s), DuraciónT(s) \n")

            initialtime = "/Calle45/" + capturehour
            initialtime = todaystr + initialtime
            # print (initialtime)

            read_esp32()  # Función de lectura ESP32

            f.close()

            # Vaciar arreglos sin eliminarlos
            maclist[:] = []
            timestartlist[:] = []
            timefinallist[:] = []
            timedurationlist[:] = []
            repetitivelist[:] = []
            userscount = 0

        today = date.today()
        todaystr = "D_" + str(today.strftime("%Y-%m-%d"))


except KeyboardInterrupt:
    print("[+] Stopping...")

ser.close()
print("[+] Done.")
