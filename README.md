# Technical Design Document (TDD)
## Arquitectura de Infraestructura de Red - TecnoNet Solutions


**Versión:** 1.0  

---

## 1. Resumen Ejecutivo

El presente documento detalla la arquitectura técnica para la modernización de la infraestructura de red corporativa de TecnoNet Solutions. El diseño tiene como objetivo reemplazar la infraestructura legada en la sede central (Costa Rica), estandarizar las operaciones en el centro regional (sede Remota) y asegurar la conectividad remota para operadores (Nicaragua), estableciendo un modelo base escalable para futuras expansiones en la región de LATAM.

La arquitectura garantiza una disponibilidad mínima del 99.5% mediante un diseño jerárquico redundante de tres capas (Núcleo, Distribución, Acceso), alta disponibilidad perimetral (HA), y segmentación segura del tráfico.

---

## 2. Arquitectura de Red (Modelo Jerárquico)

La solución se basa en el modelo de tres capas recomendado por las mejores prácticas de la industria, garantizando aislamiento de fallos, escalabilidad hasta 1.045 usuarios locales y rendimiento óptimo de los servicios.

### 2.1. Capa de Núcleo (Core)

El backbone de la red central en Costa Rica está diseñado para enrutamiento de alta velocidad y conmutación sin bloqueos.

* **Hardware:** 2x Cisco Catalyst 9300 (C9300-48UXM) ubicados en el centro de datos principal.
* **Alta Disponibilidad:** Configuración en clúster lógico mediante tecnología StackWise, operando como un único plano de control y compartiendo la función de puerta de enlace predeterminada.
* **Enrutamiento Dinámico:** Implementación de OSPF (Área 0) como protocolo de enrutamiento interior (IGP). Se inyecta explícitamente la superred corporativa `10.1.0.0/16` en el proceso OSPF del enrutador de distribución (CR-RTR-1) para garantizar que el tráfico de retorno desde los túneles VPN conozca la ruta exacta hacia las VLANs de usuarios.

### 2.2. Capa de Distribución

Esta capa actúa como límite entre las políticas de usuario y el enrutamiento de alta velocidad, consolidando los enlaces del edificio de 5 niveles.

* **Hardware:** 2x Cisco Catalyst 9300L (C9300L-48T-4G).
* **Agregación y Redundancia:** Uplinks redundantes de fibra a 10 Gbps hacia la capa de núcleo, empaquetados mediante EtherChannel (LACP) para balanceo de carga y tolerancia a fallos físicos.
* **Políticas y QoS:** Aplicación de políticas de Calidad de Servicio (QoS) para priorizar tráfico sensible a la latencia (voz IP y videoconferencia) antes de inyectarlo al backbone.

### 2.3. Capa de Acceso

Proporciona la conectividad final a los dispositivos de los usuarios corporativos, aplicando los controles de seguridad de Capa 2 (Blue Team).

* **Hardware:** 12x Cisco Catalyst 9200L (C9200L-24T-4G) distribuidos en los 5 niveles en Costa Rica, y 3 unidades en la sede Remota. Uplinks de 1 Gbps hacia distribución.
* **Segmentación Lógica:** Asignación de VLANs dedicadas por departamento operativo (VLAN 10: Soporte, VLAN 20: Finanzas, VLAN 30: Ingeniería, VLAN 40: Innovación, VLAN 50: Gerencia).
* **Seguridad de Puerto (L2):** * Implementación de `Rapid-PVST+` para convergencia acelerada del árbol de expansión.
  * Habilitación de `Spanning-Tree PortFast` exclusivo en puertos de usuario final.
  * Activación global de `BPDU Guard` para desactivar automáticamente interfaces ante la conexión no autorizada de switches de terceros (prevención de bucles).
  * Asignación de todos los puertos inactivos a una VLAN de Blackhole (ej. VLAN 999) en estado administratively down.

---

## 3. Conectividad WAN y Seguridad Perimetral

### 3.1. Acceso a Internet y Alta Disponibilidad WAN

* **Equipamiento:** 2x Routers Cisco ISR 4331 en Costa Rica operando en esquema Activo/Respaldo.
* **Conectividad:** Enlaces de fibra duales de 1 Gbps provistos por operadores locales (ej. ICE en Costa Rica, Tigo en Remota) eliminando el punto único de fallo hacia la red pública.

### 3.2. Seguridad Perimetral (NGFW)

* **Equipamiento:** Firewalls Cisco Firepower 2110 (o serie ASA en borde).
* **Control de Acceso:** Inspección profunda de paquetes y listas de control de acceso (ACL) de estado. Se implementó una arquitectura de ACL estricta ("Outside-In") evitando problemas de *Shadowing*, garantizando que el tráfico IPsec (UDP 500) y el tráfico desencapsulado retornen a la LAN sin ser descartados por reglas de denegación implícitas.

### 3.3. Interconexión VPN IPsec (Sede Nicaragua)

Para dar soporte a 400 operadores remotos en el centro de Nicaragua, se desplegó un túnel VPN Site-to-Site robusto:

* **Fase 1 (IKEv1):** Políticas endurecidas utilizando encriptación `AES-256`, hashing `SHA`, autenticación mediante llave precompartida y Diffie-Hellman `Group 5`.
* **Fase 2 (IPsec):** `Transform-set` configurado con `esp-aes-256` y `esp-sha-hmac` para asegurar la integridad y confidencialidad de la carga útil, mitigando discrepancias criptográficas entre equipos.
* **Exención de NAT:** Tráfico interesante (red `10.3.0.0/22` hacia `10.1.0.0/16`) correctamente excluido de las traducciones de direcciones (NAT0) para permitir el flujo transparente bidireccional.

---

## 4. Mitigación de Riesgos & Hardening de Infraestructura

Para evitar ataques vectoriales comunes dentro de la infraestructura local de **TecnoNet Solutions**, se aplicaron políticas estrictas de endurecimiento (*Hardening*) basadas en las mejores prácticas de Cisco y guías de la NSA:

### 4.1. Seguridad de Capa 2 (Switching Hardening)

* **Port Security:** Configuración de límites de direcciones MAC en los switches de acceso corporativos para evitar ataques de inundación de tablas MAC (*MAC Flooding*). Los puertos no utilizados fueron desactivados administrativamente (`shutdown`) y asignados a una VLAN muerta (VLAN 999).
* **DHCP Snooping & DAI:** Activación de DHCP Snooping en las VLANs de usuarios para bloquear servidores DHCP no autorizados (*Rogue DHCP*) y mitigar ataques Man-in-the-Middle (MitM), complementado con *Dynamic ARP Inspection (DAI)*.
* **Mitigación de STP Attacks:** Despliegue de `Spanning-Tree PortFast` y `BPDU Guard` en los puertos de acceso perimetrales para evitar que dispositivos de usuarios alteren la topología lógica del árbol de expansión.

### 4.2. Control de Acceso Administrativo (Plano de Gestión)

* **Acceso Seguro Exclusivo:** Desactivación absoluta de Telnet en toda la red. Toda la gestión CLI se realiza bajo **SSHv2** con criptografía RSA de 2048 bits.
* **Seguridad de Contraseñas:** Encriptación robusta de credenciales locales mediante `service password-encryption` y contraseñas de enable con algoritmos tipo `enable secret`.
* **Aislamiento de Gestión:** Creación de una VLAN de Gestión Out-of-Band (VLAN 100) exclusiva para los administradores, restringiendo el acceso administrativo desde las VLANs comunes de empleados mediante Listas de Control de Acceso (ACLs).

---

## 5. Telemetría, Observabilidad y Gestión Centralizada

Esta red tiene un monitoreo proactivo para garantizar el cumplimiento de los SLAs de disponibilidad. El diseño teórico y técnico incluye los siguientes componentes de visibilidad:

* **5.1. Recolección de Eventos (Syslog):** Todos los firewalls Cisco y routers centrales redirigen sus logs de auditoría técnica y alertas de seguridad hacia un servidor Syslog centralizado para correlación de eventos.
* **5.2. Monitoreo de Infraestructura (SNMPv3):** Implementación de SNMPv3 (garantizando autenticación y cifrado SHA/AES) para que un servidor de monitoreo central (CR-SERVER-1) vigile métricas de rendimiento como uso de CPU, memoria de los switches Catalyst y ancho de banda en interfaces WAN.
* **5.3. Análisis de Tráfico (NetFlow):** Habilitación de NetFlow en interfaces del router central `CR-RTR-1` para mapear los patrones de tráfico, identificar cuellos de botella y detectar anomalías de red o comportamientos sospechosos (como exfiltración de datos).

---

## 6. Automatización de Operaciones (NetDevOps) e Infrastructure as Data

En la carpeta `/scripts` se integró un sistema de automatización en **Python** utilizando `Netmiko` que aplica los principios de *Infrastructure as Data (IaD)*.

* **6.1. Single Source of Truth (SSoT):** En lugar de usar inventarios estáticos en código, el script interactúa programáticamente con `tabla_direccionamiento.csv`. El código extrae dinámicamente las IPs de gestión, ignora nodos no administrables (como servidores web/ISP), limpia los hostnames e infiere el sistema operativo (`cisco_ios` vs `cisco_asa`).
* **6.2. Propósito:** Ejecutar copias de seguridad de la configuración (`running-config`) de toda la topología en minutos, tolerando fallas individuales de red a través de un robusto manejo de excepciones (Try/Except).
* **6.3. Beneficio de Negocio:** Garantiza la alineación perfecta entre la documentación arquitectónica (CSV) y la ejecución operativa, previniendo derivas de configuración (*Configuration Drift*) sin sobrecarga administrativa.

---

## 7. Diseño de Direccionamiento IP (VLSM)

El esquema de direccionamiento IPv4 se planificó utilizando enrutamiento interdominios sin clases (CIDR/VLSM) sobre el bloque maestro `10.0.0.0/8`, garantizando un 20% de margen para crecimiento y minimizando el desperdicio de direcciones.

**Control de DHCP:** Para evitar colisiones de IP e interrupciones en la gestión de switches (Capa 2), los pools de DHCP en los routers de distribución incluyen exclusiones explícitas de las primeras 10 direcciones de cada subred (ej. `10.3.0.1` a `10.3.0.10`).

| Subred | Descripción | Hosts Necesarios | Máscara | Subnet ID | Rango Usable | Gateway |
| --- | --- | --- | --- | --- | --- | --- |
| **CR-N1-Soporte** | Nivel 1 CR (420 usuarios) | 420 | /22 | `10.1.0.0/22` | `10.1.0.1 - 10.1.3.254` | `10.1.0.1` |
| **CR-N3-Ingeniería** | Nivel 3 CR (310 usuarios) | 310 | /23 | `10.1.4.0/23` | `10.1.4.1 - 10.1.5.254` | `10.1.4.1` |
| **CR-N2-Finanzas** | Nivel 2 CR (160 usuarios) | 160 | /24 | `10.1.6.0/24` | `10.1.6.1 - 10.1.6.254` | `10.1.6.1` |
| **CR-N4-Innovación** | Nivel 4 CR (95 usuarios) | 95 | /25 | `10.1.7.0/25` | `10.1.7.1 - 10.1.7.126` | `10.1.7.1` |
| **CR-N5-Gerencia** | Nivel 5 CR (60 usuarios) | 60 | /26 | `10.1.7.128/26` | `10.1.7.129 - 10.1.7.190` | `10.1.7.129` |
| **Sede-Remota-Total** | 230 usuarios | 230 | /24 | `10.2.0.0/24` | `10.2.0.1 - 10.2.0.254` | `10.2.0.1` |
| **Nicaragua-VPN** | 400 operadores | 400 | /22 | `10.3.0.0/22` | `10.3.0.1 - 10.3.3.254` | `10.3.0.1` |
| **WAN-Enlaces** | Punto-punto | 2 hosts | /30 | `10.255.255.0/30` | `10.255.255.1 - 10.255.255.2` | N/A |

*(Referencia extraída del plan maestro de direccionamiento)*

---

## 8. Lista de Materiales (BoM) y Estimación Financiera

La proyección económica contempla hardware enterprise Cisco, licencias y costos operativos recurrentes. El presupuesto de inversión en capital (CAPEX) asciende a aproximadamente $255.000 USD, cubriendo la infraestructura principal.

### 8.1. Inversión en Capital (CAPEX) - Equipamiento

| Categoría | Cantidad | Costo por unidad (USD) | Subtotal (USD) |
| --- | --- | --- | --- |
| **Core switches** | 2 | 15.000 | 30.000 |
| **Switches de distribución** | 3 | 8.000 | 24.000 |
| **Switches de acceso** | 15 | 3.500 | 52.500 |
| **Routers ISR** | 3 | 10.000 | 30.000 |
| **Firewalls perimetrales** | 2 | 20.000 | 40.000 |
| **APs WiFi** | 20 | 800 | 16.000 |
| **Cables, fibra y accesorios** | - | - | 20.000 |
| **Instalación y pruebas** | - | - | 42.500 |
| **Total Estimado CAPEX** | | | **255.000 USD** |

### 8.2. Gastos Operativos Anuales (OPEX)

| Concepto | Descripción | Costo anual (USD) |
| --- | --- | --- |
| **Servicios ISP sede Costa Rica** | Dos enlaces de fibra 1 Gbps para redundancia | 60.000 |
| **Servicios ISP sede Remota** | Enlace de fibra dedicado para 230 usuarios | 24.000 |
| **Servicios en la nube** | Uso de base de datos transaccional en IBM Cloud | 24.000 |
| **Licencias y software** | Licencias de firewall, IPS, VPN y gestión de red | 18.000 |
| **Total Estimado OPEX** | | **126.000 USD** |
