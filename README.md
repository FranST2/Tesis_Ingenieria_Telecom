# Transmisor Especializado EWBS para Televisión Digital Terrestre (ISDB-Tb)

[cite_start]**Universidad de las Fuerzas Armadas ESPE** [cite: 1]
[cite_start]**Departamento de Eléctrica, Electrónica y Telecomunicaciones** [cite: 3]
[cite_start]**Autores:** Francisco Alejandro Simbaña Tasiguano y Bryan Humberto Narváez Romero [cite: 2]
**Tutor:** Msc. [cite_start]Gonzalo Fernando Olmedo Cifuentes, PhD. [cite: 6]

---

## Descripción del Proyecto
[cite_start]Este repositorio contiene el código fuente para el diseño e implementación de un transmisor dedicado para el Sistema de Alerta de Emergencias por Radiodifusión (EWBS) sobre el estándar ISDB-Tb[cite: 181]. [cite_start]El sistema permite la generación e inserción de mensajes de alerta jerarquizados (verde, amarilla y roja) en el flujo de transporte (Transport Stream), compatibles con receptores profesionales y dispositivos comerciales[cite: 1, 182, 183].

## Arquitectura del Sistema
El proyecto está dividido en dos entornos principales de procesamiento:

### 1. Análisis Forense y Extracción (MATLAB)
[cite_start]Algoritmos dedicados a la caracterización del flujo de transporte base y decodificación del estándar ARIB STD-B24[cite: 531]:
* [cite_start]Análisis estadístico de PIDs y ocupación espectral[cite: 509].
* [cite_start]Extracción de firmas digitales y delimitadores de mensajes EWBS[cite: 565, 566].
* [cite_start]Monitoreo de jerarquía PSI (Tablas PAT y PMT)[cite: 577].

### 2. Generador e Inyector EWBS (Python)
[cite_start]Aplicación principal (`generador_ewbs.py`) con interfaz gráfica desarrollada en Tkinter para entornos críticos[cite: 606, 684].
* [cite_start]**Backend:** Modulador generador de payloads mediante encapsulamiento recursivo (onion encapsulation) y cálculo de redundancia CRC-16/CRC-32[cite: 611, 621, 631].
* [cite_start]**Core:** Inyección oportunista y modificación dinámica de la tabla PMT en tiempo real[cite: 595, 636].
* [cite_start]**Frontend:** Panel de control de fácil usabilidad para secuencias de alerta y priorización[cite: 594, 684].

## Validación Experimental
[cite_start]El flujo híbrido generado ha sido validado exitosamente en hardware profesional utilizando[cite: 692, 728]:
* [cite_start]Modulador DekTec DTU-215 (VHF/UHF)[cite: 706, 710].
* [cite_start]Software de modulación StreamXpress[cite: 675].
* [cite_start]Gateway TANABIKI EGW-100 y displays LED matriciales[cite: 704, 723].

---
[cite_start]*Trabajo de integración curricular, previo a la obtención del título de Ingeniero en Telecomunicaciones.* [cite: 5]
