# Detección de fraccionamiento transaccional en Nequi

Este proyecto busca la solución de una prueba técnica de científico de datos en Nequi. Se propone un enfoque para la detección de posibles casos de fraccionamiento transaccional a partir del análisis del historial de transacciones. A diferencia de metodologías que evalúan operaciones de forma aislada, no se centra en determinar si una transacción individual presenta características atípicas. En su lugar, se orienta a identificar patrones compuestos por múltiples transacciones de bajo monto, realizadas en intervalos de tiempo cercanos, que en conjunto equivalen a un movimiento de mayor magnitud deliberadamente segmentado.

## Qué problema resuelve

La prueba técnica se enfoca en identificar una mala práctica transaccional dentro de una ventana de 24 horas. El patrón esperado comparte origen o destino lógico; además, suele verse como una ráfaga de movimientos de monto parecido.

Con los datos disponibles, eso obliga a pensar el problema como secuencia y agregación; no como clasificación fila por fila.

## Cómo está planteada la solución

El proyecto sigue una ruta sencilla y defendible:

1. Cargar y tipar los datos.
2. Limpiar lo indispensable: duplicados seguros, nulos críticos y montos no válidos.
3. Explorar el comportamiento base del conjunto de datos.
4. Definir una unidad analítica estable: `user_id + account_number + transaction_type`.
5. Construir ventanas móviles de 24 horas para cada entidad.
6. Calcular señales que ayuden a distinguir un uso normal de un patrón sospechoso.
7. Convertir esas señales en alertas operativas.

## Reglas del modelo

El modelo se basa en un enfoque de detección por reglas, lo que facilita su interpretación y trazabilidad. Esta característica resulta especialmente valiosa en contextos de validación, ya que permite explicar de manera clara el origen de cada alerta generada.

Las principales reglas consideradas son las siguientes:

- **frecuencia alta en 24 horas**;
- **monto agregado alto en 24 horas**;
- **montos poco variables dentro de la ventana**;
- **anomalía frente al patrón histórico**;
- **dispersión entre destinos observables**.

Estas reglas no operan de manera aislada, sino que se combinan para conformar distintos escenarios de riesgo. A partir de estas combinaciones, cada caso es clasificado en un nivel de prioridad, lo que permite una gestión más eficiente de las alertas:

- `pre_alerta`: una señal relevante;
- `media`: dos señales combinadas;
- `alta`: tres o más señales combinadas.

## Qué mira el detector

El detector se apoya en un conjunto acotado de señales, seleccionadas por su capacidad para capturar patrones relevantes de comportamiento:

- **frecuencia**: cuántas transacciones aparecen en la ventana;
- **monto acumulado**: cuánto suman en conjunto;
- **similitud de montos**: si los valores son muy parecidos entre sí;
- **contexto histórico**: si ese comportamiento rompe el patrón habitual de la entidad;
- **destino observable**: si las transacciones se concentran o se dispersan entre comercios y sedes.

Los umbrales utilizados no se definen de manera arbitraria; se fundamentan en percentiles derivados de los datos y en comparaciones con el comportamiento histórico específico de cada entidad.

## Qué entrega el proyecto

El resultado del proyecto consiste en una tabla de alertas diseñada para facilitar la revisión manual, proporcionando el contexto necesario para una evaluación ágil y fundamentada. Entre los campos más relevantes se incluyen:

- entidad analítica;
- inicio y fin de la ventana;
- número de transacciones;
- monto acumulado;
- señales activadas;
- nivel de alerta.

El objetivo es permitir que quien revise cada caso comprenda de forma rápida y clara las razones por las cuales fue priorizado dentro del flujo de análisis.

## Estructura del repositorio

- `notebooks/nequi_fraccionamiento.ipynb`: cuaderno principal del análisis.
- `python/utils/io.py`: carga y tipado.
- `python/utils/cleaning.py`: reglas de limpieza.
- `python/utils/eda.py`: utilidades de exploración.
- `python/utils/detection.py`: construcción del detector.
- `python/utils/validation.py`: apoyo para validación manual de alertas.

## Cómo usarlo

1. Crea un entorno virtual e instala dependencias.
2. Ubica los archivos de entrada dentro de `data/`; esa carpeta no se versiona.
3. Abre el cuaderno principal y ejecútalo en orden.

En PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
jupyter notebook notebooks/nequi_fraccionamiento.ipynb
```

## Alcance actual

Este repositorio ya tiene análisis exploratorio, reglas del detector y una salida operativa inicial. Sirve para priorizar casos y discutir el problema con criterio.

No debe leerse como un sistema final de decisión automática. Es, más bien, una primera versión analítica: clara, auditable y útil para seguir iterando.

## Limitaciones

Hay tres limitaciones que conviene dejar explícitas:

- No se cuenta con etiquetas de fraude confirmadas.
- El receptor real no está modelado de manera directa.
- Una parte importante del desempeño del detector depende de la calibración y validación de las reglas.

Precisamente por ello, el proyecto otorga un peso central al análisis, a la definición de supuestos y a la explicabilidad de cada alerta.
