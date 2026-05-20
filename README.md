# Taller 3 – Informática Médica: Procesador DICOM

**Integrante:** Juan  
**Materia:** Informática 2 – Unidad 3  
**Monitor:** Juan Esteban Pineda Lopera

---

## Descripción del proyecto

Este proyecto es una aplicación en Python que automatiza la lectura, extracción de metadatos y procesamiento de imágenes médicas en formato DICOM. Se organizó usando programación orientada a objetos (la clase `ProcesadorDICOM`) y hace uso de las librerías `pydicom`, `numpy`, `pandas` y `opencv-python`.

El flujo del programa es el siguiente:

1. Escanea un directorio en busca de archivos `.dcm`
2. Extrae los metadatos clínicos relevantes de cada archivo
3. Organiza toda esa información en un DataFrame de Pandas y la exporta a CSV
4. Calcula la intensidad promedio de los píxeles de cada imagen con NumPy
5. Aplica normalización, ecualización del histograma y detección de bordes (Canny) con OpenCV
6. Guarda las imágenes procesadas como `.png`

Los archivos DICOM usados para las pruebas son los que incluye la misma librería `pydicom` en su módulo `data/test_files`, que cuenta con más de 70 imágenes de distintas modalidades (CT, MR, US, NM, entre otras).

---

## 1. DICOM y HL7: ¿por qué son importantes y en qué se diferencian?

Cuando uno empieza a mirar cómo funciona el ecosistema de datos en salud, rápido se da cuenta de que sin estándares todo sería un caos. Los equipos médicos de distintos fabricantes generan datos en formatos propios, los hospitales usan sistemas distintos, y sin embargo un radiólogo necesita ver la imagen de un TAC tomado en otra institución. Ahí es donde entran DICOM y HL7.

**DICOM** (Digital Imaging and Communications in Medicine) es el estándar que define cómo se almacenan, transfieren y presentan las imágenes médicas. No solo guarda los píxeles: dentro de cada archivo `.dcm` va toda la información del paciente, del estudio, del equipo que tomó la imagen y los parámetros de adquisición. Eso es lo que hace que un archivo DICOM sea tan distinto a un simple `.jpg`: es una imagen más su historial clínico asociado.

**HL7** (Health Level Seven), en cambio, no tiene nada que ver con imágenes. Es un estándar de mensajería para intercambiar información clínica entre sistemas: resultados de laboratorio, órdenes médicas, altas hospitalarias, historias clínicas. Si DICOM es el lenguaje de las imágenes, HL7 es el lenguaje de los eventos clínicos.

La diferencia conceptual más clara: DICOM trabaja con archivos (un objeto por imagen), mientras que HL7 trabaja con mensajes entre sistemas (como si fueran notificaciones). En la práctica, ambos coexisten: cuando se solicita una radiografía, HL7 transmite la orden, y cuando el equipo la toma, el resultado viaja en DICOM hacia el PACS.

---

## 2. Ecualización de histograma y detección de bordes con Canny en imágenes médicas

### Ecualización del histograma (`cv2.equalizeHist`)

La idea detrás de esta técnica es redistribuir los valores de intensidad de la imagen para que el contraste sea más uniforme. En imágenes médicas esto puede ser muy útil porque muchos dispositivos generan imágenes con rangos de intensidad muy concentrados en ciertos valores, lo que hace que el ojo humano no pueda distinguir bien las estructuras.

**Ventajas:**
- Mejora visualmente el contraste en zonas que de otra manera quedarían muy oscuras o muy claras
- Es rápida de aplicar y no requiere parámetros complejos
- Sirve bien como paso previo a otros procesos (segmentación, detección de estructuras)

**Limitaciones:**
- Puede amplificar ruido en zonas homogéneas (por ejemplo, en tejido graso)
- No distingue entre contraste "clínico" y contraste artificial, por lo que puede destacar artefactos que no son estructuras reales
- En tomografías, donde los valores Hounsfield tienen significado diagnóstico específico, alterar el contraste puede desorientar al profesional

### Detección de bordes con Canny (`cv2.Canny`)

Canny es uno de los detectores de bordes más usados. Aplica dos umbrales: el inferior captura bordes suaves y el superior filtra solo los bordes fuertes. En este proyecto se usaron `threshold1=50` y `threshold2=150`, que son valores comúnmente aceptados como punto de partida. El umbral bajo de 50 permite capturar contornos leves (por ejemplo, bordes de tejido blando), mientras que el umbral alto de 150 asegura que los bordes definidos (como huesos o contrastes bien marcados) siempre sean detectados.

**Ventajas:**
- Resalta estructuras anatómicas que tienen transiciones de intensidad claras (bordes óseos, límites de órganos)
- Puede ser útil en preprocesamiento para segmentación automática o para asistir en la delimitación de regiones de interés
- Reduce la imagen a sus contornos principales, lo que facilita ciertos análisis computacionales

**Limitaciones y riesgos clínicos:**
- En imágenes con mucho ruido (por ejemplo, ecografías), Canny tiende a generar bordes falsos que no corresponden a estructuras reales
- La elección de umbrales es crítica: umbrales demasiado bajos detectan demasiado ruido, y demasiado altos pierden bordes reales importantes para el diagnóstico
- No es adecuado en modalidades como la resonancia magnética con contraste, donde los bordes relevantes pueden ser muy sutiles y fácilmente ignorados por el algoritmo

**¿Cuándo es útil y cuándo no?**

Es útil en preprocesamiento para sistemas de detección automática de fracturas o contorno de tumores en tomografías donde el contraste entre tejido sano y patológico es alto. Puede ser perjudicial si se aplica directamente sobre imágenes que un radiólogo va a interpretar, ya que distorsiona la representación original y puede ocultar información diagnóstica.

---

## 3. Dificultades encontradas e importancia de las herramientas de Python

Trabajar con archivos DICOM reales (aunque sean de prueba) enseña rápido que el estándar es mucho más complejo en la práctica que en la teoría. Algunas dificultades concretas que surgieron:

- **Tags faltantes por anonimización:** Muchos archivos de prueba no tienen `PatientName` o `PatientID` porque fueron anonimizados. Hubo que manejar eso con valores por defecto para que el DataFrame no fallara.

- **Imágenes sin datos de píxeles:** Modalidades como SR (Structured Report), RTPLAN o ECG no contienen imagen como tal. Intentar acceder a `.pixel_array` en esos casos lanza una excepción, que se maneja con `try/except`.

- **Profundidad de bits:** Las imágenes DICOM suelen ser de 12 o 16 bits, y OpenCV espera imágenes de 8 bits (uint8). La normalización fue un paso obligatorio antes de cualquier procesamiento.

- **Compresión JPEG-LS:** Algunos archivos usan codecs de compresión que pydicom no puede descomprimir por defecto sin librerías adicionales (como `pylibjpeg`). Se optó por manejar ese error y continuar con los archivos que sí se pueden leer, tal como haría un software real.

En cuanto a las herramientas, Python demostró ser una opción muy práctica para este tipo de trabajo. `pydicom` abstrae toda la complejidad del estándar DICOM en una interfaz accesible. `pandas` permitió organizar los metadatos de cientos de archivos en segundos. `numpy` facilitó el cálculo de estadísticas sobre arreglos de miles de píxeles con una sola línea. Y `opencv`, a pesar de no estar diseñado exclusivamente para imágenes médicas, provee herramientas de procesamiento muy potentes que se integran naturalmente con el ecosistema de Python.

---

## Cómo ejecutar el proyecto

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar el procesador (usa archivos DICOM de prueba de pydicom)
python procesador_dicom.py
```

Los resultados se guardan en:
- `resultados_dicom.csv` — metadatos y estadísticas de todas las imágenes
- `imagenes_procesadas/` — imágenes PNG ecualizadas y con bordes detectados

---

## Estructura del repositorio

```
.
├── procesador_dicom.py       # Código principal con la clase ProcesadorDICOM
├── requirements.txt          # Dependencias del proyecto
├── resultados_dicom.csv      # DataFrame exportado (generado al ejecutar)
├── imagenes_procesadas/      # Imágenes PNG generadas (generado al ejecutar)
└── README.md                 # Este archivo
```
