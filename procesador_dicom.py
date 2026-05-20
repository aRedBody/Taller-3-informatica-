import os
import pydicom
import numpy as np
import pandas as pd
import cv2


class ProcesadorDICOM:
    def __init__(self, directorio_salida="imagenes_procesadas"):
        self.datasets = []
        self.directorio_salida = directorio_salida
        os.makedirs(directorio_salida, exist_ok=True)

    def cargar_archivos(self, directorio):
        """Escanea el directorio y carga todos los archivos DICOM válidos."""
        self.datasets = []
        for root, _, archivos in os.walk(directorio):
            for nombre in archivos:
                ruta = os.path.join(root, nombre)
                try:
                    ds = pydicom.dcmread(ruta)
                    self.datasets.append(ds)
                except Exception:
                    pass  # Ignorar archivos que no son DICOM válidos
        print(f"Archivos DICOM cargados: {len(self.datasets)}")

    def _get_tag(self, ds, tag, default="No disponible"):
        """Obtiene un tag DICOM de forma segura."""
        try:
            valor = getattr(ds, tag, None)
            return str(valor) if valor is not None else default
        except Exception:
            return default

    def extraer_metadatos(self):
        """Extrae los metadatos relevantes de cada dataset y los organiza en un DataFrame."""
        registros = []
        for ds in self.datasets:
            registro = {
                "PatientID":        self._get_tag(ds, "PatientID"),
                "PatientName":      self._get_tag(ds, "PatientName"),
                "StudyInstanceUID": self._get_tag(ds, "StudyInstanceUID"),
                "StudyDescription": self._get_tag(ds, "StudyDescription"),
                "StudyDate":        self._get_tag(ds, "StudyDate"),
                "Modality":         self._get_tag(ds, "Modality"),
                "Rows":             self._get_tag(ds, "Rows"),
                "Columns":          self._get_tag(ds, "Columns"),
            }
            registros.append(registro)
        return pd.DataFrame(registros)

    def calcular_intensidad_promedio(self, df):
        """Calcula la intensidad promedio de píxeles de cada imagen usando NumPy."""
        intensidades = []
        for ds in self.datasets:
            try:
                intensidades.append(round(float(np.mean(ds.pixel_array)), 4))
            except Exception:
                intensidades.append(None)
        df["IntensidadPromedio"] = intensidades
        return df

    def procesar_con_opencv(self, df):
        """Normaliza, ecualiza el histograma y aplica Canny a cada imagen DICOM."""
        for i, ds in enumerate(self.datasets):
            try:
                pixels = ds.pixel_array

                # Manejar imágenes 3D: RGB (H,W,3) o multi-frame (frames,H,W)
                if pixels.ndim == 3:
                    if pixels.shape[2] in (3, 4):  # RGB o RGBA
                        pixels = cv2.cvtColor(pixels, cv2.COLOR_RGB2GRAY)
                    else:  # multi-frame: tomar el primer corte
                        pixels = pixels[0]

                # 1. Normalización a uint8 (0-255)
                p_min, p_max = pixels.min(), pixels.max()
                if p_max > p_min:
                    normalizada = ((pixels - p_min) / (p_max - p_min) * 255).astype(np.uint8)
                else:
                    normalizada = np.zeros_like(pixels, dtype=np.uint8)

                # 2. Ecualización del histograma
                ecualizada = cv2.equalizeHist(normalizada)

                # 3. Detección de bordes con Canny
                # Umbral bajo=50 para capturar bordes suaves, alto=150 para bordes fuertes
                bordes = cv2.Canny(ecualizada, threshold1=50, threshold2=150)

                # 4. Guardar imágenes procesadas
                uid = df.iloc[i]["StudyInstanceUID"].replace(".", "_")[:25]
                nombre_base = f"img_{i:03d}_{uid}"
                cv2.imwrite(os.path.join(self.directorio_salida, f"{nombre_base}_ecualizada.png"), ecualizada)
                cv2.imwrite(os.path.join(self.directorio_salida, f"{nombre_base}_bordes.png"), bordes)

            except Exception as e:
                print(f"  [Aviso] Imagen {i} sin datos de píxeles accesibles: {e}")

    def ejecutar(self, directorio):
        """Ejecuta el pipeline completo de procesamiento DICOM."""
        print("=" * 55)
        print("  PROCESADOR DICOM - Informática Médica")
        print("=" * 55)

        print("\n[1/4] Cargando archivos DICOM...")
        self.cargar_archivos(directorio)

        print("[2/4] Extrayendo metadatos...")
        df = self.extraer_metadatos()

        print("[3/4] Calculando intensidades promedio (NumPy)...")
        df = self.calcular_intensidad_promedio(df)

        print("[4/4] Procesando imágenes con OpenCV...")
        self.procesar_con_opencv(df)

        print("\n--- Resumen del DataFrame ---")
        print(df[["PatientID", "Modality", "Rows", "Columns", "IntensidadPromedio"]].to_string(index=False))

        csv_path = "resultados_dicom.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8")
        print(f"\nResultados exportados a: {csv_path}")
        print(f"Imágenes guardadas en:   {self.directorio_salida}/")
        print("=" * 55)

        return df


if __name__ == "__main__":
    import pydicom.data

    # Usar los archivos de prueba que incluye la librería pydicom
    directorio_dicom = os.path.join(os.path.dirname(pydicom.data.__file__), "test_files")

    procesador = ProcesadorDICOM(directorio_salida="imagenes_procesadas")
    df_resultados = procesador.ejecutar(directorio_dicom)
