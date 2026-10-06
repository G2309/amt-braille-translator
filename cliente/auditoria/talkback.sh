# Recorrido de la PWA con TalkBack en el emulador de Android (imagen google_apis con root); requiere adb y el teclado del emulador en /dev/input/event1
# Navegación con TalkBack por teclado y registro de lo que dice
dicho() { adb logcat -d | grep "SpeechControllerImpl: Speaking fragment" | sed 's/.*text="\(.*\)", utteranceId.*/\1/'; }
tecla() { adb logcat -c; adb shell input keycombination "$@"; sleep 2.5; dicho | tr '\n' '|'; echo; }
TECLADO=/dev/input/event1
# Pulsa una combinación en el teclado físico del emulador: códigos Linux de las teclas, la última se suelta primero
combo() { local s=""; for k in "$@"; do s="$s sendevent $TECLADO 1 $k 1; sendevent $TECLADO 0 0 0;"; done
  for k in $(echo "$@" | tr ' ' '\n' | tac); do s="$s sendevent $TECLADO 1 $k 0; sendevent $TECLADO 0 0 0;"; done
  adb shell "$s"; }
siguiente() { adb logcat -c; combo 125 106; sleep 2.5; dicho | tr '\n' '|'; echo; }
# Mueve el foco de TalkBack y devuelve lo que dijo; activar usa Acción + Espacio
paso() { adb logcat -c; combo 125 "$1"; sleep "${2:-3.5}"; dicho | tr '\n' ' '; echo; }
recorrer() { local previo=""; for i in $(seq 1 "${1:-20}"); do d=$(paso 106); [ -z "$d" ] && d="(sin voz)"; echo "$i	$d"; [ "$d" = "$previo" ] && break; previo="$d"; done; }
# Busca hacia atrás o adelante hasta que TalkBack diga el texto buscado
buscar() { local dir=$2; for i in $(seq 1 ${3:-25}); do d=$(paso $dir); case "$d" in *"$1"*) echo "encontrado: $d"; return 0;; esac; done; echo "no encontrado"; return 1; }
activar() { adb logcat -c; combo 125 57; sleep "${1:-4}"; dicho | tr '\n' ' '; echo; }
