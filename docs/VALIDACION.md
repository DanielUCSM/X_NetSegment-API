# Registro de validación de NetSegment API

Fecha: 4 de octubre de 2026, America/Lima. Versión del sistema: 1.0.0. Grupo: 13.

| Verificación | Evidencia | Resultado |
|---|---|---|
| Pruebas automatizadas | python -m pytest -q | 37 pruebas correctas |
| Dependencias | python -m pip check | No broken requirements found |
| Servidor ASGI real | Proceso Uvicorn en puerto local | Inicio correcto |
| Disponibilidad | GET /health | 200, ok, versión 1.0.0 |
| FLSM | /24 y cuatro subredes | 200, /26 |
| VLSM | /22, hosts 500, 120, 50 y 2 | 200, 708 direcciones ocupadas |
| CIDR | Cuatro /24 consecutivas alineadas | 200, 192.168.0.0/22 |
| IPv4 inválida | Octeto 300 | 422 |
| Capacidad insuficiente | 500 hosts en /24 | 400 |
| Contrato | GET /openapi.json | Archivo generado en docs/openapi.json |

El servidor se inició en un subproceso y se cerró al terminar las comprobaciones. El puerto 18000 se utilizó para la prueba; el valor por defecto es 8000. No se dejó un servicio público desplegado.

Entorno: Linux x86_64, Python 3.12.14. Se registró una advertencia de deprecación de Starlette sobre httpx, sin fallos en las pruebas.

No se midieron carga, latencias ni concurrencia máxima. No se ejecutó systemd en un servidor remoto, no se verificó Windows/macOS y no se implementó IPv6.

La revisión administrativa utiliza la estructura de nombre 13_NetSegmentAPI y verifica la invitación institucional a jangulo@ucsm.edu.pe. Curso: Computación en Red III.
