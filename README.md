# Karaoke Inteligente

Ejercicio optativo de recuperación — Introducción a la Programación y Computación 2  
Universidad de San Carlos de Guatemala · Facultad de Ingeniería  
**Estudiante:** Jonathan Jeanfranco Chirix Santizo · **Carné:** 202307900

Aplicación que muestra la letra de las canciones **línea por línea, al ritmo del cantante**,
para que el público pueda acompañarlo sin adelantarse ni atrasarse.

| Modo | Cómo funciona |
|---|---|
| **Manual (m)** | El operador escribe 2–3 palabras que escucha; el programa identifica canción y línea y avanza con (c). |
| **Automático (a)** | Una IA de voz a texto escucha al cantante, identifica la canción y la letra avanza sola a su velocidad (predictor-corrector). Si la canción no existe, la captura en tablas temporales para revisarla. |

## Descargar e instalar (usuarios)
Los instaladores están en **[Releases](../../releases)**:

| Plataforma | Archivo | Instalación |
|---|---|---|
| Windows 10/11 | `Karaoke Inteligente-x.y.z.msi` | Doble clic → asistente. Si aparece "Windows protegió su PC": *Más información → Ejecutar de todas formas*. |
| Android 8+ | `karaoke-x.y.z.apk` | Abrir el archivo → permitir *Instalar apps desconocidas* → *Instalar*. Al entrar al modo automático, permitir el micrófono. |

No se necesita instalar Python ni nada más.

## Menú principal
`(m)` manual · `(a)` automático · `(f)` alimentación [(t) archivo, (e) manual, (v) revisar capturas] ·
`(p)` programa del cantante · `(w)` listar de 10 en 10 · `(x)` ver letra por código ·
`(u)` corregir letra · `(b)` borrar canción · `(k)` configuración · `(d)` diagnóstico

Durante la canción: `(c)` continuar · `(a)` atrás · `(l)` línea igual · `(r)` repetir canción ·
`(i)` ignorar · `(s)` seguir · `(n)` otra canción · `(m)` pasar a manual · `(f)` finalizar.

## Tecnologías
Python 3.13 · BeeWare (Toga + Briefcase) · SQLite · whisper.cpp (Windows) ·
reconocedor de voz de Android (vía Chaquopy) · numpy · sounddevice

## Compilar desde el código (desarrolladores)
```powershell
py -3.13 -m venv C:\Proyectos\venvs\karaoke
C:\Proyectos\venvs\karaoke\Scripts\Activate.ps1
python -m pip install briefcase
$env:BRIEFCASE_HOME = "C:\BeeWare"            # ruta sin espacios
powershell -ExecutionPolicy Bypass -File scripts\descargar_whisper.ps1
briefcase dev                                  # ejecutar desde el código
briefcase dev --test                           # pruebas (pytest)
briefcase package windows --adhoc-sign         # instalador .msi en dist\
briefcase package android -p debug-apk         # app .apk en dist\
```

## Estructura
```
src/karaoke/
  app.py, config.py, plataforma.py
  datos/       base CANCIONES y repositorios
  nucleo/      texto, importador, buscador, programa
  audio/       motores de voz (Whisper, Android, simulado) y limpieza del audio
  automatico/  sincronizador, aprendiz (canciones nuevas), sesión
  vistas/      pantallas Toga
  resources/   ejemplos, íconos y whisper (este último lo descarga el script)
tests/         pruebas automáticas
docs/          manual de usuario y manual técnico
```
