# Transmisor Especializado EWBS para Televisión Digital Terrestre (ISDB-Tb)

**Universidad de las Fuerzas Armadas ESPE**<br>
**Departamento de Eléctrica, Electrónica y Telecomunicaciones**<br>
**Autores:** Francisco Alejandro Simbaña Tasiguano y Bryan Humberto Narváez Romero<br>
**Tutor:** Msc. Gonzalo Fernando Olmedo Cifuentes, PhD.

---

## Descripción del Proyecto
Este repositorio contiene el código fuente para el diseño e implementación de un transmisor dedicado para el Sistema de Alerta de Emergencias por Radiodifusión (EWBS) sobre el estándar ISDB-Tb. El sistema permite la generación e inserción de mensajes de alerta jerarquizados (verde, amarilla y roja) en el flujo de transporte (Transport Stream), compatibles con receptores profesionales y dispositivos comerciales.

## Arquitectura del Sistema
El proyecto está dividido en dos entornos principales de procesamiento:

### 1. Análisis Forense y Extracción (MATLAB)
Algoritmos dedicados a la caracterización del flujo de transporte base y decodificación del estándar ARIB STD-B24:
* Análisis estadístico de PIDs y ocupación espectral.
* Extracción de firmas digitales y delimitadores de mensajes EWBS.
* Monitoreo de jerarquía PSI (Tablas PAT y PMT).

### 2. Generador e Inyector EWBS (Python)
Aplicación principal (`generador_ewbs_final_v28.py`) con interfaz gráfica desarrollada en Tkinter para entornos críticos.
* **Backend:** Modulador generador de payloads mediante encapsulamiento recursivo (onion encapsulation) y cálculo de redundancia CRC-16/CRC-32.
* **Core:** Inyección oportunista y modificación dinámica de la tabla PMT en tiempo real.
* **Frontend:** Panel de control de fácil usabilidad para secuencias de alerta y priorización.

## Validación Experimental
El flujo híbrido generado ha sido validado exitosamente en hardware profesional utilizando:
* Modulador DekTec DTU-215 (VHF/UHF).
* Software de modulación StreamXpress.
* Gateway TANABIKI EGW-100 y displays LED matriciales.

---
*Trabajo de integración curricular, previo a la obtención del título de Ingeniero en Telecomunicaciones.*
