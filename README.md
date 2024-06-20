# PSB-ECG
Interfaz médica y procesamiento de señales de electrocardiograma

## Set up
Se conecta la placa Arduino al integrado AD8232 el cual se conecta a los 3 electrodos de ECG (RA, LA, LL).

## Archivo .ino
Se corre en Arduino IDE para programar la placa.

## Archivo .ui
Con Designer se crea una interfaz para recompilar datos del paciente y del registro del ECG.

## Archivo .py
Contiene las funciones necesarias para llamar a la interfaz y procesar la data. Devuelve la frecuencia cardíaca y la gráfica del ECG en tiempo real. Se guarda la información en archivos .txt (datos del paciente) y .csv (valores ECG).

## Archivo .ipynb
Informe de lo realizado y procesamiento offline del intervalo QT y su correción.
