#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# LuoOS — code-server process manager
# Usage: ./code_server_manager.sh [start|stop|status|restart]
# ═══════════════════════════════════════════════════════════════════════

LUO_WORKSPACE="$HOME/luo_workspace"
CODE_SERVER_PORT=8080
CODE_SERVER_CONFIG="$HOME/.config/code-server/config.yaml"
PID_FILE="/tmp/luo-code-server.pid"
LOG_FILE="/tmp/luo-code-server.log"

is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            return 0
        fi
    fi
    # Also check by port
    if lsof -Pi :$CODE_SERVER_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    else
        lsof -Pi :$CODE_SERVER_PORT -sTCP:LISTEN -t 2>/dev/null | head -1
    fi
}

cmd_start() {
    if is_running; then
        echo "code-server already running (PID: $(get_pid))"
        echo "URL: http://localhost:$CODE_SERVER_PORT"
        exit 0
    fi

    mkdir -p "$LUO_WORKSPACE"

    echo "Starting code-server..."
    nohup code-server \
        --config "$CODE_SERVER_CONFIG" \
        "$LUO_WORKSPACE" \
        >> "$LOG_FILE" 2>&1 &

    PID=$!
    echo $PID > "$PID_FILE"

    # Wait for startup
    for i in {1..20}; do
        sleep 0.5
        if curl -s "http://localhost:$CODE_SERVER_PORT" >/dev/null 2>&1; then
            echo "code-server started (PID: $PID)"
            echo "URL: http://localhost:$CODE_SERVER_PORT"
            exit 0
        fi
    done

    echo "code-server started (may still be initializing)"
    echo "URL: http://localhost:$CODE_SERVER_PORT"
}

cmd_stop() {
    if ! is_running; then
        echo "code-server not running"
        exit 0
    fi

    PID=$(get_pid)
    if [ -n "$PID" ]; then
        kill "$PID" 2>/dev/null
        rm -f "$PID_FILE"
        echo "code-server stopped (PID: $PID)"
    fi
}

cmd_status() {
    if is_running; then
        PID=$(get_pid)
        echo "running"
        echo "PID: $PID"
        echo "URL: http://localhost:$CODE_SERVER_PORT"
        echo "Workspace: $LUO_WORKSPACE"
    else
        echo "stopped"
    fi
}

cmd_restart() {
    cmd_stop
    sleep 1
    cmd_start
}

case "${1:-status}" in
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    status)  cmd_status ;;
    restart) cmd_restart ;;
    *)
        echo "Usage: $0 [start|stop|status|restart]"
        exit 1
        ;;
esac
