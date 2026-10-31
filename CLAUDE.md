# CLAUDE.md — Contexto del proyecto Karaoke Inteligente

## Quién y qué
- Estudiante: Jonathan Jeanfranco Chirix Santizo (Jean), carné 202307900, USAC, curso IPC2.
- Ejercicio optativo de recuperación "Karaoke Inteligente" (12 pts: 6 Windows + 6 Android, SIN punteo parcial).
- **Entrega: sábado 31/10/2026 antes de las 20:00** a innovacion.usac@gmail.com. Meta interna: enviar a las 18:30.
- Idioma: responder siempre en español, tono informal y directo.

## Forma de trabajo (preferencias de Jean)
- Entregar SIEMPRE archivos completos ya corregidos, nunca "cambia la línea X".
- Commit al cerrar cada cambio, con Conventional Commits en español: `fix(ambito): descripcion`.
- En guías paso a paso con interfaz en inglés: dar la traducción al español y decir exactamente cuándo tomar captura (📸).
- Explicar brevemente el porqué de cada cambio (él debe poder defender cada línea).

## Entorno (Windows de Jean)
- Proyecto: `C:\Proyectos\IPC2_KaraokeInteligente_202602_202307900`
- Repo: https://github.com/jeansitox5/IPC2_KaraokeInteligente_202602_202307900 (ramas `main` y `develop`; se trabaja en `develop`).
- venv (FUERA del repo): `C:\Proyectos\venvs\karaoke` con **Python 3.13.17** (no 3.14: toga-winforms/pythonnet).
  Activar: `C:\Proyectos\venvs\karaoke\Scripts\Activate.ps1`
- Variables de usuario: `BRIEFCASE_HOME=C:\BeeWare`, `GRADLE_USER_HOME=C:\BeeWare\gradle` (la carpeta de usuario "Jan Chirix" tiene espacio).
- Briefcase 0.4.7, Toga 0.5.7. adb: `C:\BeeWare\tools\android_sdk\platform-tools\adb.exe`
- Teléfono de pruebas: Samsung Galaxy A35 5G (depuración USB). Hay también un emulador `beePhone-31`.
- PowerShell 5.1: un programa nativo que escribe en stderr aparece como "NativeCommandError" aunque funcione.

## Comandos
```powershell
briefcase dev --test                      # 20 pruebas (pytest) — deben pasar todas
briefcase dev -r                          # ejecutar la app desde el código
powershell -ExecutionPolicy Bypass -File scripts\descargar_whisper.ps1   # ya ejecutado OK
briefcase create windows                  # recrear si cambian pyproject/íconos/recursos
briefcase package windows --adhoc-sign    # dist\Karaoke Inteligente-<ver>.msi
briefcase create android                  # recrear si cambian permisos/íconos
briefcase run android                     # elegir el Galaxy A35
briefcase run android -u                  # tras cambios de código
briefcase package android -p debug-apk    # dist\Karaoke Inteligente-<ver>.debug.apk
adb logcat -s python.stdout python.stderr # errores de Python en el teléfono
```

## Arquitectura (src/karaoke)
- `app.py`: KaraokeInteligente(toga.App); es el "contexto" (db, canciones, programa, temporales, cfg, buscador); `mostrar(pantalla)`, `crear_motor()`.
- `config.py` (DEFAULTS + Configuracion), `plataforma.py` (Windows/Android, selector de archivos con Intent en Android, permiso RECORD_AUDIO).
- `datos/`: base_datos (CANCIONES.db en app.paths.data; detecta/crea; tablas NOMBRES, LETRAS, PROGRAMA, TMP_NOMBRES, TMP_LETRAS, CONFIGURACION, HISTORIAL), repositorios.
- `nucleo/`: texto (normalizar), importador (t), buscador (buscar_fragmento manual; alinear/posiciones automático con puntaje = 0.5·chars reescalado + 0.5·fracción de palabras), programa.
- `audio/`: motor_voz (MotorVoz, Observacion, MotorSimulado, filtro alucinaciones), captura (sounddevice/WAV), limpieza (numpy: DC, banda 80-4000, resta espectral, normalizar, VAD), whisper_win (whisper-cli.exe en resources/whisper, ventana 4 s / salto 2 s), voz_android (SpeechRecognizer vía Chaquopy dynamic_proxy, resultados parciales, reinicio continuo).
- `automatico/`: sincronizador (estados ESCUCHANDO/IDENTIFICANDO/SIGUIENDO/FIN/CAPTURANDO NUEVA; predictor-corrector p̂=p+v·(t−t_ref), corrección 0.6, congela sin voz 1.5 s, adelanto 0.5 s), aprendiz (canciones nuevas → TMP_*), sesion (cola + historial + programa).
- `vistas/`: base, inicio (menú m a f p w x u b k d + tecla rápida en Windows), karaoke (vista compartida), modo_manual, modo_automatico, alimentacion (t e v), consultas (w x u b), programa (p), configuracion (k), diagnostico (d).
- Teclas: c continuar, a atrás, l línea igual, r repetir, i ignorar, s seguir, n otra, m a manual, f fin. (Suposición S1: (i)=ignorar; línea igual = (l)).
- pyproject: Windows requiere toga-winforms, numpy, sounddevice; Android solo toga-android; `cleanup_paths` quita resources/whisper del APK; `permission.microphone`.

## Estado (31/10, 10:00)
- [x] Código completo; commits C3–C8 en develop y push hecho.
- [x] Whisper descargado y funcionando (`whisper-cli -h` OK).
- [x] `briefcase dev --test`: 20 passed. `briefcase dev -r`: la app abre sin errores.
- [ ] Confirmar comportamiento real del modo automático en Windows (identifica / sigue ritmo).
- [ ] Commit pendiente del script corregido: `fix(scripts): verificación de whisper-cli compatible con PowerShell 5.1`.
- [ ] Android en el A35 REAL (nunca probado en dispositivo real; voz_android.py y el selector de archivos Android no se han ejecutado aún). Revisar con adb logcat.
- [ ] Subir version en pyproject a 1.0.0, `briefcase create` + package de Windows y Android; probar .msi en otra PC.
- [ ] Release v0.9.0 (Windows) y v1.0.0 (final con .msi, .apk y PDFs) en GitHub.
- [ ] Manuales: Jean tiene Manual_Usuario.docx y Manual_Tecnico.docx con recuadros "📸 CAPTURA"; insertar capturas, actualizar índice, exportar PDF, copiar a docs/.
- [ ] Correo de entrega con enlaces al Release (instaladores > 25 MB) y PDFs adjuntos.

## Prioridad si falta tiempo
Recortar: videos → afinamientos del automático. NUNCA recortar: instaladores probados, pruebas en el A35, manuales, envío.
