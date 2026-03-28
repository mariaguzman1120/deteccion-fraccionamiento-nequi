# Detección de fraccionamiento transaccional en Nequi

Este proyecto propone una forma de detectar posibles casos de fraccionamiento transaccional a partir de historial de transacciones. La idea no es mirar una operación aislada y adivinar si “se ve rara”. La lógica es otra: buscar varias transacciones pequeñas, cercanas en el tiempo, que juntas se comportan como un movimiento grande partido en pedazos.

Dicho en simple, es parecido a cuando alguien reparte un pago grande en varios pagos pequeños para no llamar la atención. Cada transacción, por sí sola, puede parecer normal; la señal aparece cuando se observan en conjunto.

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

La salida no es una “verdad absoluta”. Es una tabla priorizada de casos para revisión.

## Qué mira el detector

El detector combina pocas señales, pero bien elegidas:

- **frecuencia**: cuántas transacciones aparecen en la ventana;
- **monto acumulado**: cuánto suman en conjunto;
- **similitud de montos**: si los valores son muy parecidos entre sí;
- **contexto histórico**: si ese comportamiento rompe el patrón habitual de la entidad;
- **destino observable**: si las transacciones se concentran o se dispersan entre comercios y sedes.

Los cortes no se fijan “a ojo”. Se apoyan en percentiles observados en los datos y en comparaciones contra el comportamiento histórico de cada entidad.

## Reglas del modelo

El modelo está construido como un detector basado en reglas. Eso ayuda mucho en una prueba como esta, porque cada alerta se puede explicar.

Las reglas principales son estas:

- **frecuencia alta en 24 horas**;
- **monto agregado alto en 24 horas**;
- **montos poco variables dentro de la ventana**;
- **anomalía frente al patrón histórico**;
- **dispersión entre destinos observables**.

Esas reglas no viven solas. Se combinan en escenarios; después, cada caso cae en un nivel de prioridad:

- `pre_alerta`: una señal relevante;
- `media`: dos señales combinadas;
- `alta`: tres o más señales combinadas.

## Qué entrega el proyecto

El resultado esperado es una tabla de alertas con contexto suficiente para revisión manual. Entre los campos más útiles están:

- entidad analítica;
- inicio y fin de la ventana;
- número de transacciones;
- monto acumulado;
- señales activadas;
- nivel de alerta.

La intención es práctica: que quien revise un caso entienda rápido por qué quedó arriba en la cola.

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

Hay tres límites que conviene dejar explícitos:

- no hay etiquetas confirmadas de fraude;
- el receptor real no está modelado de forma directa;
- parte del valor del detector depende de cómo se calibren y validen las reglas.

Justamente por eso el proyecto pone tanto peso en el análisis, en los supuestos y en la explicabilidad de la alerta.
