#!/bin/bash
# Luo Shell — Luo OS v0.1
# Built by Abd El-Rahman Abbas (Mr. Kai)

RED='\033[0;91m'; GRN='\033[0;92m'; YLW='\033[0;93m'
BLU='\033[0;96m'; MAG='\033[0;95m'; DIM='\033[2m'; RST='\033[0m'; BLD='\033[1m'

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HISTORY="$HOME/.luo_history"
touch "$HISTORY"

clear
echo -e "${BLU}${BLD}"
echo "  _     _   _  ___       ___  _   _  ___ _     _     "
echo " | |   | | | |/ _ \     / __|| | | |/ __| |   | |    "
echo " | |   | | | | (_) |    \__ \| |_| |\__ \ |__ | |__  "
echo " |_|   |___|_|\___/     |___/ \___/ |___/____|____|   "
echo -e "${RST}${DIM}  Luo OS v0.1 — Free for Humans & AI Agents${RST}"
echo ""

help_menu() {
    echo -e "${BLD}Commands:${RST}"
    echo -e "  ${BLU}ai / agent${RST}   Start Luo Agent (local AI)"
    echo -e "  ${BLU}daemon${RST}       Run Luo Agent as background daemon"
    echo -e "  ${BLU}desktop${RST}      Launch desktop GUI"
    echo -e "  ${BLU}api${RST}          Start Agent API :7070"
    echo -e "  ${BLU}rest${RST}         Start REST API :8080"
    echo -e "  ${BLU}boot${RST}         Boot all OS services"
    echo -e "  ${BLU}agents${RST}       List registered AI agents"
    echo -e "  ${BLU}status${RST}       OS service status"
    echo -e "  ${BLU}info${RST}         System information"
    echo -e "  ${BLU}memory${RST}       Show Luo Agent memory"
    echo -e "  ${BLU}sysmon${RST}       Live system monitor"
    echo -e "  ${BLU}pkg <cmd>${RST}    Package manager"
    echo -e "  ${BLU}help${RST}         This menu"
    echo -e "  ${BLU}exit${RST}         Exit"
    echo -e "${DIM}  All bash commands also work.${RST}"
}

os_status() {
    echo -e "${BLD}Service Status${RST}"
    echo "────────────────────────────────"
    python3 -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('127.0.0.1',7070)); s.close()" 2>/dev/null \
        && echo -e "  ${GRN}● Agent API    :7070${RST}" || echo -e "  ${RED}● Agent API    offline${RST}"
    python3 -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('127.0.0.1',8080)); s.close()" 2>/dev/null \
        && echo -e "  ${GRN}● REST API     :8080${RST}" || echo -e "  ${RED}● REST API     offline${RST}"
    curl -s http://localhost:11434/api/tags > /dev/null 2>&1 \
        && echo -e "  ${GRN}● Ollama       online${RST}" || echo -e "  ${RED}● Ollama       offline${RST}"
    echo "────────────────────────────────"
    python3 --version 2>&1
}

sysmon() {
    while true; do
        clear
        echo -e "${BLU}${BLD}Luo OS — System Monitor${RST}  $(date '+%H:%M:%S')"
        echo "─────────────────────────────────────"
        free -h | awk 'NR==2{printf "Memory: total=%s used=%s free=%s\n",$2,$3,$4}'
        df -h / | awk 'NR==2{printf "Disk:   total=%s used=%s free=%s (%s)\n",$2,$3,$4,$5}'
        echo "Processes: $(ps aux | wc -l)"
        sleep 2
    done
}

echo -e "${DIM}Type 'help' for commands.${RST}"
echo ""

while true; do
    DIR=$(pwd | sed "s|$HOME|~|")
    echo -en "${GRN}${BLD}luo${RST}${BLU}@os${RST}:${MAG}${DIR}${RST}${YLW}\$${RST} "
    read -r -e cmd
    [ -z "$cmd" ] && continue
    echo "$cmd" >> "$HISTORY"
    case "$cmd" in
        help)    help_menu ;;
        info)    uname -a && python3 --version ;;
        status)  os_status ;;
        sysmon)  sysmon ;;
        ai|agent)
            cd "$ROOT/luo_agent" && python3 luo_agent.py; cd "$ROOT" ;;
        daemon)
            cd "$ROOT/luo_agent" && python3 luo_agent.py --daemon &
            cd "$ROOT"; echo -e "${GRN}Daemon started (PID $!)${RST}" ;;
        desktop)
            python3 "$ROOT/ui/window_manager.py" & ;;
        api)
            python3 "$ROOT/ai_core/agent_api.py" &
            echo -e "${GRN}Agent API started (PID $!)${RST}" ;;
        rest)
            python3 "$ROOT/ai_core/rest_api.py" &
            echo -e "${GRN}REST API started (PID $!)${RST}" ;;
        boot)
            python3 "$ROOT/luo_init.py" & ;;
        agents)
            python3 -c "
import sys; sys.path.insert(0,'$ROOT')
from ai_core.agent_identity import LuoIdentity
LuoIdentity.print_registry()" ;;
        memory)
            M="$HOME/.luo_agent/MEMORY.md"
            [ -f "$M" ] && cat "$M" || echo "No memory yet. Run Luo Agent first." ;;
        pkg*)
            python3 "$ROOT/shell/luo_pkg.py" ${cmd#pkg} ;;
        exit|quit)
            echo -e "${DIM}Goodbye from Luo OS.${RST}"; break ;;
        *)   eval "$cmd" ;;
    esac
done
