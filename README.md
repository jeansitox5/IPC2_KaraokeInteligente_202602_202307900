# Karaoke Inteligente

Ejercicio optativo de recuperación – Introducción a la Programación y Computación 2  
Universidad de San Carlos de Guatemala · Facultad de Ingeniería

**Estudiante:** Jonathan Jeanfranco Chirix Santizo · **Carné:** 202307900

## Descripción
Aplicación que muestra la letra de las canciones línea por línea, sincronizada con
el cantante. Tiene un modo manual (el operador busca la canción con 2–3 palabras) y
un modo automático (reconocimiento de voz que identifica la canción y sigue al
cantante). Las canciones se guardan en una base de datos SQLite llamada CANCIONES.

## Plataformas
| Plataforma | Instalador | Motor de voz |
|---|---|---|
| Windows 10/11 | `.msi` | Whisper (whisper.cpp, local) |
| Android 8+ | `.apk` | Reconocedor de voz de Android |

Los instaladores se publican en la sección **Releases** de este repositorio.

## Tecnologías
Python 3.13 · BeeWare (Toga + Briefcase) · SQLite · whisper.cpp · numpy · sounddevice

## Ejecutar desde el código (desarrollo)
```powershell
py -3.13 -m venv venv
venv\Scripts\Activate.ps1
python -m pip install briefcase
briefcase dev
```

## Estado
🚧 En desarrollo.