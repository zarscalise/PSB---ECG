import sys
import numpy as np
from PyQt5 import QtWidgets, QtCore
from pyqtgraph import PlotWidget
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.uic import loadUi
import serial
import time
import pandas as pd
from pathlib import Path
import scipy.signal as signal


datos_ECG = []
fs = 200


class VentanaPrincipal(QMainWindow):


    def __init__(self):
        super(VentanaPrincipal, self).__init__()
        loadUi(r"/Users/zarscalise/Desktop/PSBTP2GRUPO5.ui", self)


        self.bt_cerrar.clicked.connect(lambda: self.close())
        self.bt_minimizar.clicked.connect(self.control_bt_normal)
        self.bt_menos.clicked.connect(self.control_bt_minimizar)
        self.bt_maximizar.clicked.connect(self.control_bt_maximizar)


        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)
        self.setWindowOpacity(1)


        self.botondatos.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.page_datos))
        self.botonver.clicked.connect(lambda: self.stackedWidget.setCurrentWidget(self.page_graf))
        self.botoniniciar.clicked.connect(self.start)
        self.botonpausa.clicked.connect(self.stop)
        self.botonconectar.clicked.connect(self.conectar_arduino)
        self.botonguardar.clicked.connect(self.archivar)
        self.botonclear.clicked.connect(self.borrar)


        self.w1 = self.grafico.addPlot(row=0, col=0, title='ECG')
        self.serialArduino = None


    def control_bt_minimizar(self):
        self.showMinimized()


    def control_bt_normal(self):
        self.showNormal()
        self.bt_minimizar.hide()
        self.bt_maximizar.show()


    def control_bt_maximizar(self):
        self.showMaximized()
        self.bt_minimizar.show()
        self.bt_maximizar.hide()


    def mousePressEvent(self, event):
        self.click_position = event.globalPos()


    def archivar(self):
            t = np.arange(0, len(datos_ECG) / fs, 1 / fs)
            datos_dic = {'tiempo': t, 'datos_ECG': datos_ECG}
            datos_df = pd.DataFrame.from_dict(datos_dic)
            directorio = Path(r"/Users/zarscalise/Desktop")
            nombre = self.editnombre.text()
            archivo_csv = directorio.joinpath(nombre + '_ECG.csv')
            datos_df.to_csv(archivo_csv, index=False)
            edad = self.editedad.text()
            fecha = self.fechanac.date()
            sexo = self.sexobox.currentText()
            comentar = self.editcomentarios.text()
            bpm = self.label_bpm.text()

            fechita = fecha.toString()
            if directorio.is_dir():
                archivo_txt = directorio.joinpath(nombre + '.txt')
                with open(archivo_txt, 'w') as f:
                    f.write(
                        f"DATOS CARGADOS: \n"
                        f"NOMBRE: {nombre}\n"
                        f"EDAD: {edad}\n"
                        f"FECHA: {fechita}\n"
                        f"SEXO: {sexo}\n"
                        f"COMENTARIOS: {comentar}\n"
                        f"BPM: {bpm}\n"
                    )
                print("Creado con exito")
            else:
                print("No existe el directorio")

    def conectar_arduino(self):
        try:
            self.serialArduino = serial.Serial(port='/dev/cu.usbmodem14201', baudrate=9600, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=0.5)
            time.sleep(1)
            print('Conexion exitosa')
            print("connected to: " + self.serialArduino.portstr)
            time.sleep(1)
        except Exception as e:
            print(f"Error conectando al Arduino: {e}")


    # Aca arrancan las funciones que uso para el Pan-Tompkins 

    
    def filtrado(self, valores): 
        # la idea es aplicar la funcion de transferencia PASABAJOS: 𝐻(𝑧)=〖(1−𝑧^(−6))〗^2/〖(1−𝑧^(−1))〗^2
    
        # Coeficientes del numerador (1 - 2z^-6 + z^-12)
        num_pb = [1, 0, 0, 0, 0, 0, -2, 0, 0, 0, 0, 0, 1]
        
        # Coeficientes del denominador  (1 - 2z^-1 + z^-2)
        denom_pb = [1, -2, 1]

        # High-pass filter coefficients
        num_pa = [-1/32, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1/32]
        denom_pa = [1, -1]

        num = np.convolve(num_pb, num_pa)
        denom = np.convolve(denom_pb, denom_pa)
        
        # Apply the filter using lfilter
        ECG_filtrado = signal.lfilter(num, denom, valores)
        
        return ECG_filtrado

    
    def derivativo_y_cuadrado(self, valores):
        # Coeficientes para H(z) = 0.1(2 + z^-1 - z^-3 - 2z^-4)
        num_der = [0.2, 0.1, 0, -0.1, -0.2]
        denom_der = [1]  # es 1 para filtro FIR 
        
        # Aplicar filtro
        ECG_derivado = signal.lfilter(num_der, denom_der, valores)

        # Elevar al cuadrado
        ECG_cuadrado = np.square(ECG_derivado)

        return ECG_cuadrado


    def integracion(self, valores):
        #para integrar 𝑦(𝑛𝑇)=1/𝑁 [𝑥(𝑛𝑇−(𝑁−1)𝑇+𝑥(𝑛𝑇−(𝑁−2)𝑇+⋯+𝑥(𝑛𝑇)]
        # Inicializar el array con 0
        ECG_integrado = np.zeros(len(valores))
        N = 30 #tamaño de la ventana
        # Realizar la integración usando una ventana deslizante

        for i in range(N, len(valores)):
            ECG_integrado[i] = np.sum(valores[i-N:i]) / N # ej si i=10, N=3 --> [10-3:10] selecciona los elementos en los índices 7, 8, y 9 
        
        return ECG_integrado


    def PanTompkins(self, valores, fs):
        ECG_filtrado = self.filtrado(valores)
        ECG_derivado_cuadrado = self.derivativo_y_cuadrado(ECG_filtrado)
        ECG_integrado = self.integracion(ECG_derivado_cuadrado)

        umbral = 0.7*max(ECG_integrado) #viendo el grafico de la filtada

        peaks, _ = signal.find_peaks(ECG_integrado, height=umbral, distance = (0.6*fs))

        duracion_minutos = len(ECG_integrado) / (fs * 60)

        cantidad_latidos = len(peaks)

        bpm = cantidad_latidos / duracion_minutos

        return bpm 


    def graficar(self):
        if self.serialArduino and self.serialArduino.isOpen():
            signalI = []
            self.serialArduino.write(b's')
            valSI = self.serialArduino.read(size=200)
            for i in range(0, len(valSI) - 1, 2):
                val2 = ord(valSI[i:i+1])
                val3 = ord(valSI[i+1:i+2])
                val4 = val2 * 256 + val3
                signalI.append(val4 * 5 / 1023) #conversión bits a volts

            datos_ECG.extend(signalI)
            #print(time.time())
           
            if len(datos_ECG) >= 2000:
                x_position = np.arange(len(datos_ECG) - 2000, len(datos_ECG)) / fs
                y_position = datos_ECG[len(datos_ECG) - 2000:len(datos_ECG)]

                frecuencia_cardiaca = self.PanTompkins(datos_ECG, fs)
                self.label_bpm.setText(str(int(frecuencia_cardiaca))) #Actualizar el label_bpm con el valor de la frecuencia cardíaca

                self.w1.plot(x_position, y_position, pen='r', clear=True)
                self.w1.showAxis('left', True)
                self.w1.showLabel('left', show=True)
                self.w1.setMenuEnabled('left', True)
                self.w1.setMenuEnabled('bottom', True)
                self.w1.viewRect()
                self.w1.showGrid(x=True, y=True, alpha=0.5)
                self.w1.setXRange(x_position[0], x_position[-1])
                ax0 = self.w1.getAxis('bottom')
                ax0.setStyle(showValues=True)
            else:
                print("No hay suficientes datos para graficar (se necesitan al menos 2000 puntos)")
        else:
            print("Arduino no conectado")


    def start(self):
        self.timerA = QtCore.QTimer()
        self.timerA.timeout.connect(self.graficar)
        self.timerA.start(500)


    def stop(self):
        print('stop')
        self.timerA.stop()


    def borrar(self):
        datos_ECG.clear()
        self.w1.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    mi_app = VentanaPrincipal()
    mi_app.show()
    sys.exit(app.exec_())







