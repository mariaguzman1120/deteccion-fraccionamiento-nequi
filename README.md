# Detección de fraccionamiento transaccional en Nequi

Este repositorio documenta una propuesta analítica para identificar posibles casos de fraccionamiento transaccional a partir de información histórica de transacciones. La idea no es perseguir una transacción aislada, sino encontrar un patrón: varias operaciones pequeñas, cercanas en el tiempo, que juntas se comportan como una transacción mayor fragmentada.

Este proyecto se apoya en tres frentes: exploración rigurosa del *dataset*, formulación de hipótesis de negocio y construcción de un detector explicable que pueda operar como producto de datos.

## Problema de negocio

Según la consigna de la prueba, el fraccionamiento transaccional ocurre cuando una operación de mayor valor se divide en varias transacciones más pequeñas que, sumadas, representan el valor de la transacción original. Ese patrón suele ocurrir dentro de una ventana de 24 horas y comparte el mismo origen o destino lógico.

Llevado a un caso cotidiano, es parecido a partir una compra grande en muchos pagos pequeños para no llamar la atención del control. Visto transacción por transacción, cada movimiento puede parecer normal; visto como secuencia, ya no.

## Objetivo del proyecto

Diseñar un detector analítico que permita:

- identificar ventanas de 24 horas con señales compatibles con fraccionamiento transaccional;
- priorizar casos para revisión operativa mediante niveles de alerta;
- dejar una ruta clara para convertir el análisis en un producto de datos reproducible.

## Criterio del enfoque

El fenómeno descrito por la prueba no se entiende bien mirando filas sueltas. Se entiende mejor cuando se agrupan transacciones por entidad, se ordenan en el tiempo y se observan como una secuencia dentro de una ventana de 24 horas.

Por eso el proyecto se apoya en un detector basado en reglas, señales agregadas y comparación contra el comportamiento observado de cada entidad. Es un enfoque práctico, explicable y fácil de auditar; además, permite priorizar casos sin depender de supuestos difíciles de sostener con la información disponible.

## Datos disponibles

El esquema descrito en el PDF incluye estas columnas:

- `_id`
- `merchant_id`
- `subsidiary`
- `transaction_date`
- `account_number`
- `user_id`
- `transaction_amount`
- `transaction_type`

Hay una limitación importante desde el inicio: el receptor no está modelado de forma explícita. `merchant_id` y `subsidiary` funcionan como destino observable en algunos casos; `account_number` requiere interpretación cuidadosa, porque el PDF no aclara si representa origen, destino o la cuenta desde la que se registra el evento.

## Enfoque analítico

La solución se construyó en cinco bloques.

### 1. Carga y tipado

La lectura del parquet se hace con `pandas`; en ese paso se tipa `transaction_date` y se derivan `transaction_day` y `transaction_time` para facilitar análisis temporales y agregaciones.

### 2. Reglas operativas de limpieza

Antes de modelar, se aplican reglas mínimas y explícitas:

- eliminación de duplicados seguros de `_id`;
- remoción de filas con nulos en campos obligatorios para el análisis;
- exclusión de montos menores o iguales a cero.

La idea es simple: si la señal transaccional está rota desde la base, cualquier detector posterior hereda ese ruido.

### 3. EDA guiado por hipótesis

El análisis exploratorio no se planteó como una galería de gráficos. Se enfocó en responder preguntas útiles para la detección:

- ¿qué tan concentrado está el tráfico por `merchant_id` y `subsidiary`?
- ¿cómo se distribuyen los montos por `transaction_type`?
- ¿cuál es la frecuencia típica por usuario?
- ¿qué tan larga es la cola de usuarios con alta actividad?

### 4. Unidad de análisis y ventana temporal

La unidad analítica elegida en el *notebook* es:

`user_id + account_number + transaction_type`

Se trabaja sobre ventanas móviles de 24 horas. Para cada ventana se calculan señales que apuntan al fenómeno buscado.

### 5. Motor de escenarios

En lugar de una única regla rígida, el detector activa escenarios de riesgo. Cada escenario representa una manifestación plausible del fraccionamiento; la combinación de escenarios define el nivel final de alerta.

## Features del detector

El detector utiliza variables de cinco grupos.

| Grupo | Señales principales |
| --- | --- |
| Frecuencia | número de transacciones en 24 horas |
| Monto | suma, promedio y desviación estándar del monto en la ventana |
| Similitud | coeficiente de variación de montos dentro de la ventana |
| Contexto histórico | desviación del día frente al comportamiento observado de la misma entidad |
| Destino observable | concentración y dispersión entre `merchant_id` y `subsidiary` |

En términos prácticos, la lógica es esta: si una entidad hace muchas transacciones en poco tiempo, con montos parecidos, hacia un destino observable consistente —o repartidas artificialmente entre sedes—, la sospecha sube.

## Reglas del modelo

El modelo no decide por una sola condición aislada. Primero calcula señales; después activa reglas simples y auditables. Esa separación importa, porque permite explicar por qué una alerta subió de prioridad.

Las reglas planteadas son estas:

- **R1. Frecuencia alta en 24 horas**: una entidad supera el umbral alto de número de transacciones dentro de la ventana móvil. La intención es capturar ráfagas transaccionales.
- **R2. Monto agregado alto en 24 horas**: la suma de transacciones de la ventana supera un umbral alto para su segmento. No busca el ticket individual alto; busca el monto total reconstruido por agregación.
- **R3. Montos similares**: el coeficiente de variación de la ventana es bajo. Si los montos son muy parecidos entre sí, la señal es más compatible con fraccionamiento deliberado que con actividad variada y orgánica.
- **R4. Anomalía frente al comportamiento habitual**: el día observado se desvía de la referencia histórica de la misma entidad en frecuencia, en monto, o en ambos. Esta regla intenta separar uso intensivo normal de un cambio de patrón.
- **R5. Dispersión sobre destino observable**: la actividad de la entidad se reparte entre varias `subsidiary` o varios destinos observables; la señal se vuelve más fuerte si esa dispersión ocurre bajo un `merchant_id` dominante.

En la implementación actual, los umbrales de frecuencia y monto se segmentan por `transaction_type`, mientras que la anomalía histórica se aproxima con *z-scores* diarios de frecuencia y monto. No es un sistema cerrado ni definitivo; es una base operativa razonable para una primera versión.

## Cómo se definen los thresholds

Los *thresholds* no están fijados a mano con un número arbitrario único para todo el sistema. Se calculan a partir de la distribución observada en los datos, para que el detector compare cada caso contra una referencia empírica y no contra una intuición suelta.

La lógica actual es esta:

- **Threshold de frecuencia alta**: se calcula por `transaction_type` como un percentil alto del número de transacciones en la ventana de 24 horas. En la implementación actual se usa el percentil 95.
- **Threshold de monto agregado alto**: también se calcula por `transaction_type`, usando un percentil alto de la suma de montos dentro de la ventana. En la implementación actual se usa el percentil 95.
- **Threshold de baja variación**: se calcula sobre el coeficiente de variación (`cv`) de los montos en la ventana. Como aquí interesa detectar homogeneidad, no se usa la cola alta sino la cola baja de la distribución; en la implementación actual se usa el percentil 25.
- **Threshold de anomalía histórica**: para cada entidad se construye una referencia diaria de frecuencia y monto, y luego se calcula qué tan lejos cae el día observado respecto a ese comportamiento. En la tabla final, una señal se considera anómala cuando el *z-score* es al menos 2.

Ese esquema tiene dos ventajas claras. Primero, adapta el detector a la escala real de cada tipo transaccional; segundo, evita que una misma regla castigue por igual comportamientos que viven en distribuciones distintas.

También conviene dejar explícito qué significa esto en operación: un threshold no define fraude, solo define rareza relativa dentro del patrón observado. La alerta aparece cuando esa rareza se combina con otras señales compatibles con fraccionamiento.

## Escenarios de riesgo implementados

El motor final de escenarios contempla cuatro patrones:

- `burst_similar`: combina R1 y R3. Representa una ráfaga de transacciones con montos muy parecidos dentro de 24 horas.
- `burst_anomalous`: combina R1 y R4. Representa una ráfaga que, además, rompe el patrón histórico de la entidad.
- `material_amount`: combina R2 con R3 o R4. Representa una ventana cuyo monto agregado ya es material, y que además muestra homogeneidad o anomalía.
- `destination_dispersion`: combina R1 y R5. Representa una ráfaga que se distribuye entre varios puntos operativos observables.

La salida operativa se resume así:

- `pre_alerta`: se activa un escenario;
- `media`: se activan al menos dos escenarios;
- `alta`: se activan tres o más escenarios.

## Qué aporta el EDA

El análisis exploratorio cumple un papel concreto: no está para “mostrar gráficos”, sino para justificar las reglas del detector.

En este problema, el EDA permite verificar al menos cuatro cosas:

- si la distribución de montos es asimétrica y tiene cola larga;
- si la frecuencia por usuario o por cuenta es heterogénea;
- si existen concentraciones fuertes por `merchant_id` o `subsidiary`;
- si conviene comparar cada entidad contra su propio comportamiento histórico, en lugar de usar una referencia global única.

Ese paso es clave. Sin ese contexto, un detector basado solo en conteos terminaría confundiendo actividad intensiva legítima con mala práctica transaccional.

## Producto de datos propuesto

La salida esperada del detector es una tabla de alertas con contexto suficiente para auditoría y priorización. Entre los campos más relevantes están:

- entidad analítica: `user_id`, `account_number`, `transaction_type`;
- ventana evaluada: `window_start`, `window_end`;
- intensidad del patrón: `tx_count_24h`, `amount_24h`, `cv_amount_24h`;
- contexto observable: `top_merchant_id`, `top_subsidiary`, participaciones y dispersiones;
- evidencia histórica: `z_day_tx_count`, `z_day_amount`;
- decisión final: `scenario_count`, `alert_level`, `is_alert`.

Eso permite que una alerta no llegue “vacía”. Llega con motivo, contexto y trazabilidad.

## Flujo de datos propuesto

El flujo lógico del producto de datos es este:

1. Ingesta de transacciones desde la capa cruda.
2. Validación de esquema, tipado y reglas básicas de calidad.
3. Construcción de una capa curada de transacciones limpias.
4. Cálculo de features de ventana y agregados de contexto.
5. Ejecución del motor de escenarios.
6. Persistencia de la tabla de alertas.
7. Revisión manual de alertas priorizadas y retroalimentación del sistema.

En una arquitectura real, este flujo se beneficiaría de tres capas separadas —cruda, curada y analítica— para evitar recalcular todo desde cero y para mantener trazabilidad sobre cada decisión.

## Frecuencia de actualización recomendada

La frecuencia depende del objetivo operativo.

- Si el objetivo inicial es monitoreo y priorización, una corrida diaria en *batch* es suficiente.
- Si el objetivo es detección oportuna para actuar dentro del mismo ciclo operativo, una actualización horaria es más adecuada.

La recomendación práctica para una primera versión es comenzar con procesamiento diario; después, si el equipo operativo puede absorber la carga y el costo lo justifica, mover el detector a una cadencia horaria.

## Estructura del repositorio

```text
.
├── README.md
├── requirements.txt
├── notebooks/
│   └── nequi_fraccionamiento.ipynb
├── python/
│   ├── __init__.py
│   └── utils/
│       ├── __init__.py
│       ├── cleaning.py
│       ├── detection.py
│       ├── eda.py
│       └── io.py
└── data/
    ├── raw/
    ├── outputs/
    ├── samples/
    ├── Prueba Técnica Científico de datos en NEQUI.pdf
    └── sample_user_id_50.parquet
```

### Qué hace cada módulo

- `python/utils/io.py`: carga y tipado base de los datos.
- `python/utils/cleaning.py`: reglas de limpieza y deduplicación.
- `python/utils/eda.py`: funciones de análisis exploratorio y visualización.
- `python/utils/detection.py`: construcción de features, reglas heurísticas y tabla final de alertas.
- `notebooks/nequi_fraccionamiento.ipynb`: narrativa principal del análisis, desde la exploración hasta el detector.

## Cómo ejecutar el proyecto

### 1. Crear y activar un entorno virtual

En Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```


### 4. Abrir el *notebook*

```bash
jupyter notebook notebooks/nequi_fraccionamiento.ipynb
```

El *notebook* puede revisarse también a partir de sus salidas guardadas. Conviene leerlas como evidencia exploratoria sobre una muestra de trabajo reducida, no como un reporte final de producción sobre el universo completo de datos.

## Idea central del proyecto

La apuesta de este repositorio es deliberada: primero hay que demostrar que el patrón existe, que puede describirse con evidencia y que la alerta resultante le sirve a alguien del lado operativo.

Ese es el corazón de la solución propuesta aquí.
