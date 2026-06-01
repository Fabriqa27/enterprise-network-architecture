import os
import csv
from datetime import datetime
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException


# Credenciales globales 
USERNAME = os.getenv("NET_USER", "admin")
PASSWORD = os.getenv("NET_PASS", "Cisco123")
SECRET = os.getenv("NET_SECRET", "Cisco123")

def get_devices_from_ssot(filepath):
    """
    Lee la Tabla de Direccionamiento (SSoT), extrae los equipos de red válidos,
    limpia los nombres y autodetecta el sistema operativo (IOS vs ASA).
    """
    devices = []
    processed_hosts = set() # Evitar duplicados si hay múltiples interfaces.
    
    try:
        with open(filepath, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file) # Lee automáticamente los encabezados de tu CSV
            
            for row in reader:
                raw_name = row.get("Dispositivo", "")
                ip = row.get("IP_Asignada", "")
                
                # 1. Ignorarar filas vacías, Servidores, equipos de ISP o interfaces virtuales SVI.
                ignored_keywords = {"Servidor", "ISP", "SVI"}
                if not raw_name or not ip:
                    continue
                if any(word in raw_name for word in ignored_keywords):
                    continue
                    
                # 2. Limpieza de Hostname
                hostname = raw_name.split()[0]
                
                # 3. IP de gestión
                if hostname not in processed_hosts:
                    # 4. Inferencia de Sistema Operativo
                    if "FW" in hostname:
                        dev_type = "cisco_asa"
                    elif "SW" in hostname or "RTR" in hostname:
                        dev_type = "cisco_ios"
                    else:
                        print(f"No se pudo identificar el tipo de {hostname}, usando IOS.")
                        dev_type = "cisco_ios"
                    

                    devices.append({
                        "device_type": dev_type,
                        "host": ip,
                        "username": USERNAME,
                        "password": PASSWORD,
                        "secret": SECRET,
                        "hostname": hostname
                    })
                    processed_hosts.add(hostname)
                    
    except FileNotFoundError:
        print(f"[!] Error Crítico: No se encontró la SSoT en {filepath}")
        
    return devices

def backup_device(device):
    """Se conecta al dispositivo, extrae la configuración y la guarda localmente."""
    hostname = device.pop("hostname") # Nombre del archivo
    net_connect = None

    try:
        print(f"\n[Respaldando {hostname} ({device['host']}) - SO: {device['device_type']}...")

        # Conexión SSH
        net_connect = ConnectHandler(**device)
        net_connect.enable()

        # Extracción de configuración
        output = net_connect.send_command("show running-config")

        # Formato de guardado
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"backups/{hostname}_{date_str}.txt"

        with open(filename, "w") as backup_file:
            backup_file.write(output)

        print(f"Éxito: Guardado en {filename}")

    except NetmikoAuthenticationException:
        print(f"Autenticación fallida para {hostname} ({device.get('host')})")
    except NetmikoTimeoutException:
        print(f"Timeout al conectar con {hostname} ({device.get('host')})")
    except Exception as e:
        print(f"Error respaldando {hostname} ({device.get('host')}): {e}")
    finally:
        if net_connect:
            try:
                net_connect.disconnect()
            except Exception:
                pass


if __name__ == "__main__":
    if not os.path.exists("backups"):
        os.makedirs("backups")
        
    print(" Sistema de Automatización NetDevOps ")
    
    #  Se apunta directamente a el archivo CSV maestro
    ssot_file = "../docs/tabla_direccionamiento.csv" if os.path.exists("../docs/tabla_direccionamiento.csv") else "tabla_direccionamiento.csv"
    
    network_devices = get_devices_from_ssot(ssot_file)
    
    if not network_devices:
        print(" No hay dispositivos gestionables en la matriz.")
    else:
        print(f"[*] Se extrajeron {len(network_devices)} equipos de red para backup.")
        for target in network_devices:
            backup_device(target)
            
    print("\nTarea de Respaldo Finalizada.")