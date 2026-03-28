# Modelo de detección de fraccionamiento transaccional

## 1. Objetivo

El objetivo del modelo es identificar ventanas de 24 horas en las que una misma entidad analítica presenta un patrón compatible con fraccionamiento transaccional: varias transacciones pequeñas, cercanas en el tiempo, que en conjunto equivalen a un movimiento materialmente mayor.

La solución implementada en el pipeline no es un clasificador supervisado ni un detector de anomalías genérico. Es un detector heurístico basado en escenarios, construido para ser:

- explicable;
- trazable;
- auditable;
- fácil de convertir en producto operativo.

## 2. Modelo elegido

El modelo final usado por el pipeline es:

`python/utils/detection.py -> build_scenario_detection_table(...)`

Ese flujo construye una tabla diaria por entidad y asigna escenarios de riesgo, un `alert_level` y una variable operativa `is_alert`.

Nota importante:

- el repositorio también conserva una ruta alternativa basada en score heurístico (`build_detection_table`);
- sin embargo, la versión final elegida para el pipeline es la basada en escenarios, porque es más alineada con la consigna del problema y más interpretable para revisión manual.

## 3. Unidad de análisis

La entidad analítica por defecto es:

`user_id + account_number + transaction_type`

Esta decisión busca equilibrar tres cosas:

- capturar comportamiento individual;
- mantener consistencia operativa por cuenta;
- evitar mezclar créditos y débitos en una misma señal.

Sobre esa entidad se construyen ventanas móviles de 24 horas y luego se consolida una fila por entidad y por día.

## 4. Flujo estadístico del modelo

El flujo que sigue el detector es este:

1. Cargar y limpiar la base transaccional.
2. Construir features de ventana móvil de 24 horas.
3. Seleccionar la última ventana observada por entidad y día.
4. Construir una referencia histórica diaria por entidad.
5. Construir features de destino observable.
6. Calcular umbrales por segmento.
7. Activar hipótesis y escenarios.
8. Traducir esos escenarios a niveles de alerta.

## 5. Definiciones estadísticas

### 5.1. Features de ventana de 24 horas

Sea una ventana de 24 horas con montos:

`x_1, x_2, ..., x_n`

Las métricas principales son:

```text
tx_count_24h = n

amount_24h = Σ x_i

avg_amount_24h = (1 / n) * Σ x_i

std_amount_24h = sqrt( Σ (x_i - x̄)^2 / (n - 1) )

cv_amount_24h = std_amount_24h / avg_amount_24h
```

Interpretación:

- `tx_count_24h` mide frecuencia;
- `amount_24h` mide materialidad agregada;
- `avg_amount_24h` resume el ticket medio;
- `std_amount_24h` mide dispersión absoluta;
- `cv_amount_24h` mide dispersión relativa y ayuda a detectar montos muy parecidos entre sí.

El coeficiente de variación es útil aquí porque el fraccionamiento suele verse como una ráfaga de montos similares, no simplemente como una suma alta.

### 5.2. Consolidación diaria

El detector no usa todas las ventanas como salida final. Para evitar múltiples alertas redundantes del mismo día, se toma:

- la última ventana observada por entidad y día.

Eso produce una fila diaria por entidad analítica.

### 5.3. Baseline histórico diario

Para cada entidad y día se construyen:

```text
day_tx_count = número de transacciones del día

day_amount = monto total del día
```

Luego, para cada entidad, se estima su referencia histórica:

```text
user_avg_day_tx = media histórica de day_tx_count
user_std_day_tx = desviación estándar histórica de day_tx_count

user_avg_day_amount = media histórica de day_amount
user_std_day_amount = desviación estándar histórica de day_amount
```

Con eso se calculan z-scores:

```text
z_day_tx_count = (day_tx_count - user_avg_day_tx) / user_std_day_tx

z_day_amount = (day_amount - user_avg_day_amount) / user_std_day_amount
```

Interpretación:

- un z-score alto en frecuencia indica que el día actual es inusualmente intenso frente al comportamiento normal de esa entidad;
- un z-score alto en monto indica que el monto del día rompe el patrón histórico, aun si el valor absoluto no parece extremo a nivel global.

### 5.4. Features de destino observable

Dado que no existe una columna de receptor explícita, el modelo usa proxies observables:

- `merchant_id`;
- `subsidiary`;
- `account_number`.

Para cada entidad y día se calculan métricas de concentración y dispersión.

Ejemplos:

```text
merchant_tx_share = merchant_tx_count / total_tx_del_día

merchant_amount_share = merchant_amount / total_amount_del_día

subsidiary_tx_share = subsidiary_tx_count / total_tx_del_día

account_tx_share = account_tx_count / total_tx_del_día
```

También se resumen:

- número de merchants únicos;
- número de subsidiarias únicas;
- número de cuentas únicas;
- participación del merchant dominante;
- participación de la subsidiaria dominante;
- máximo número de subsidiarias dentro de un mismo merchant.

## 6. Umbrales del modelo

### 6.1. Umbrales por segmento

El detector no define los umbrales “a mano”. Los estima por segmento, donde por defecto:

`segment_cols = ['transaction_type']`

Los umbrales son:

```text
tx_count_threshold = Q_0.95(tx_count_24h | transaction_type)

amount_threshold = Q_0.95(amount_24h | transaction_type)

cv_low_threshold = Q_0.25(cv_amount_24h | transaction_type)
```

Interpretación:

- una ventana está en frecuencia alta si cae por encima del percentil 95 de frecuencia de su segmento;
- una ventana está en monto alto si cae por encima del percentil 95 de monto agregado de su segmento;
- una ventana tiene baja variabilidad si cae por debajo del percentil 25 del coeficiente de variación de su segmento.

### 6.2. Umbral fijo de anomalía histórica

Para la referencia contra histórico se usa:

```text
z_score_threshold = 2.0
```

Esto significa que el día actual debe estar al menos dos desviaciones estándar por encima del promedio histórico de la entidad para ser considerado anómalo.

### 6.3. Mínimo operativo de transacciones

Además se exige:

```text
min_tx_count = 3
```

Esto evita disparar casos con una o dos operaciones aisladas, que no representan bien la idea de fraccionamiento.

## 7. Reglas base

A partir de las métricas anteriores se construyen reglas base binarias.

### 7.1. Frecuencia alta en 24 horas

```text
high_tx_count_24h = 1 si:

tx_count_24h >= tx_count_threshold
AND tx_count_24h >= 3
```

### 7.2. Monto agregado alto en 24 horas

```text
high_amount_24h = 1 si:

amount_24h >= amount_threshold
AND tx_count_24h >= 3
```

### 7.3. Montos poco variables

```text
low_cv_24h = 1 si:

cv_amount_24h <= cv_low_threshold
AND tx_count_24h >= 3
```

### 7.4. Anomalía contra histórico

```text
anomalous_tx_count = 1 si z_day_tx_count >= 2.0

anomalous_amount = 1 si z_day_amount >= 2.0
```

### 7.5. Dispersión de destinos observables

El modelo resume tres patrones:

```text
multi_merchant_dispersion = 1 si n_unique_merchants > 1 y tx_count >= 3

multi_subsidiary_dispersion = 1 si n_unique_subsidiaries > 1 y tx_count >= 3

multi_subsidiary_same_merchant = 1 si:
top_merchant_tx_share >= 0.80
AND n_unique_subsidiaries > 1
AND tx_count >= 3
```

Luego se consolida:

```text
h4_destination_dispersion = 1 si cualquiera de las tres reglas anteriores se activa
```

## 8. Escenarios finales

Las reglas base no se usan de forma aislada. Se combinan en escenarios con significado de negocio.

### 8.1. Ráfaga con montos similares

```text
scenario_burst_similar = 1 si:

high_tx_count_24h = 1
AND low_cv_24h = 1
```

Lectura:

- muchas transacciones;
- montos muy parecidos;
- patrón clásico de fraccionamiento.

### 8.2. Ráfaga anómala frente al histórico

```text
scenario_burst_anomalous = 1 si:

high_tx_count_24h = 1
AND (anomalous_tx_count = 1 OR anomalous_amount = 1)
```

Lectura:

- la entidad tuvo una ráfaga;
- además, el comportamiento es raro para su propia historia.

### 8.3. Monto agregado material

```text
scenario_material_amount = 1 si:

high_amount_24h = 1
AND (
  low_cv_24h = 1
  OR anomalous_amount = 1
  OR anomalous_tx_count = 1
)
```

Lectura:

- el agregado de la ventana ya es material;
- además, la forma del patrón sugiere intencionalidad.

### 8.4. Dispersión entre destinos observables

```text
scenario_destination_dispersion = 1 si:

high_tx_count_24h = 1
AND h4_destination_dispersion = 1
```

Lectura:

- hay alta frecuencia;
- las operaciones no solo son muchas, también muestran dispersión entre merchants o sedes, o reparto entre subsidiarias de un mismo merchant.

## 9. Nivel de alerta

El modelo final calcula:

```text
scenario_count = suma de escenarios activos
```

Luego asigna:

```text
pre_alerta  -> scenario_count = 1
media       -> scenario_count >= 2
alta        -> scenario_count >= 3
```

Y define:

```text
is_alert = 1 si alert_level es media o alta
```

Interpretación operativa:

- `pre_alerta` sirve como señal débil o caso a monitorear;
- `media` y `alta` son backlog accionable para revisión manual;
- `alta` concentra la mayor intensidad heurística.

## 10. Por qué elegimos este enfoque y no un modelo no supervisado de ML

La ausencia de etiquetas reales no implica automáticamente que la mejor decisión sea usar ML no supervisado. En este problema, un modelo no supervisado era una opción posible, pero no la más defendible como primera versión.

### 10.1. Razones para no elegirlo como solución final

#### a. El problema ya viene definido por hipótesis de negocio

La consigna describe explícitamente un patrón:

- varias transacciones pequeñas;
- en una ventana de 24 horas;
- con mismo origen o destino lógico;
- que en conjunto representan una transacción mayor.

Eso no se parece a un problema de “anomalía genérica”, sino a un problema de detección de patrón específico. Cuando el patrón ya tiene semántica clara, un detector por reglas bien diseñado suele ser más apropiado que un score opaco.

#### b. La explicabilidad es un requisito central

El resultado debe servir para revisión manual y discusión operativa. Con un enfoque heurístico se puede explicar cada alerta con frases concretas:

- alta frecuencia;
- montos similares;
- anomalía frente al histórico;
- dispersión entre destinos.

En cambio, con modelos como Isolation Forest, LOF, clustering o autoencoders, la salida típica es un score de rareza cuya explicación no siempre es directa para negocio.

#### c. El esquema de datos tiene ambigüedades

No existe un receptor explícito. El destino se infiere parcialmente mediante `merchant_id` y `subsidiary`. En ese contexto, un detector no supervisado puede capturar rarezas de estructura de datos, pero no necesariamente el patrón de fraccionamiento que realmente interesa.

#### d. La calibración de un no supervisado es más difícil sin verdad terreno

En modelos no supervisados siempre aparece el problema de:

- cuántos outliers asumir;
- dónde poner el umbral;
- cómo distinguir rareza estadística de riesgo real;
- cómo evitar penalizar comportamientos legítimos poco frecuentes.

Sin etiquetas confirmadas, esa calibración suele terminar dependiendo igual de reglas, revisión experta y criterio manual.

#### e. La solución debía convertirse en producto de datos operativo

Para una primera versión operativa, es más valioso entregar:

- una tabla de alertas con motivos;
- reglas auditables;
- thresholds revisables;
- trazabilidad por caso.

Eso acelera la validación con negocio y facilita iteración.

### 10.2. Qué problemas podría tener un no supervisado aquí

Si se hubiera usado un modelo no supervisado como solución principal, los riesgos más probables serían:

- alta sensibilidad a escalas y distribución sesgada de montos;
- mezcla de rareza global con comportamiento legítimo de nichos;
- scores difíciles de traducir en acciones operativas;
- mayor dificultad para justificar por qué un caso fue marcado;
- necesidad de mucho feature engineering adicional para incorporar secuencia temporal y contexto histórico.

### 10.3. Cuándo sí tendría sentido usarlo más adelante

Un modelo no supervisado o semi-supervisado sí podría ser útil en una segunda etapa, por ejemplo para:

- descubrir patrones no cubiertos por las reglas actuales;
- complementar el motor heurístico con un score adicional;
- priorizar revisión dentro de `pre_alerta`;
- comparar cobertura entre reglas explícitas y rareza estadística.

Pero eso tendría más sentido después de contar con:

- validación manual de alertas;
- retroalimentación operativa;
- eventualmente etiquetas débiles o casos confirmados.

## 11. Cómo interpretar la salida final

La tabla final del pipeline contiene, entre otras, estas columnas:

- entidad analítica;
- `window_start` y `window_end`;
- `tx_count_24h`;
- `amount_24h`;
- `cv_amount_24h`;
- `z_day_tx_count`;
- `z_day_amount`;
- escenarios activados;
- `scenario_count`;
- `alert_level`;
- `is_alert`.

Lectura práctica:

- si un caso tiene `scenario_count = 1`, es una señal débil;
- si tiene `scenario_count >= 2`, entra a backlog accionable;
- si tiene `scenario_count >= 3`, es una prioridad alta;
- el campo de motivos en el HTML traduce esos escenarios a lenguaje entendible.

## 12. Conclusión

La elección metodológica no fue “evitar ML”, sino elegir la herramienta más apropiada para la madurez actual del problema.

En esta prueba:

- no hay etiquetas confirmadas;
- el patrón de interés está bien descrito;
- la explicabilidad importa tanto como la detección;
- el resultado debe ser operativo.

Por eso, la decisión más sólida fue construir un detector heurístico basado en escenarios, con fundamento estadístico, interpretable y listo para evolucionar hacia enfoques híbridos más adelante.
