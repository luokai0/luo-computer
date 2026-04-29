# luo_os Docker Sandbox

One command to run the full luo_os environment.

## Run
```bash
docker run -p 6080:6080 -p 11434:11434 luokai25/luo_os
```

Then open: http://localhost:6080/vnc.html

Click **Connect** — you'll see the luo_os desktop.

## What's inside

| Service | Port | Description |
|---------|------|-------------|
| QEMU    | —    | luo_os kernel running |
| noVNC   | 6080 | Desktop in browser |
| Ollama  | 11434| Local AI (llama3.2) |
| Agent   | 7777 | AI agent serial bridge |

## Build locally
```bash
git clone https://github.com/luokai25/luo_os
cd luo_os
docker build -t luo_os .
docker run -p 6080:6080 luo_os
```

## Use the AI

In the luo_os terminal:
ai how do i write a loob in c?
help
cat > .dockerignore << 'EOF'
target/
luowm/target/
*.o
*.iso
*.bin
isodir/
.git/
agent/__pycache__/
agent/agent.log
agent/commands.json
agent/results.json
