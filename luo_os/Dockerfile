FROM ubuntu:24.04

LABEL maintainer="luokai25"
LABEL description="luo_os sandbox — Human + AI desktop OS"
LABEL version="1.0"

ENV DEBIAN_FRONTEND=noninteractive
ENV OLLAMA_HOST=0.0.0.0:11434

# install all tools
RUN apt-get update && apt-get install -y \
    qemu-system-x86 \
    grub-pc-bin \
    grub-common \
    xorriso \
    nasm \
    gcc \
    make \
    mtools \
    python3 \
    python3-pip \
    curl \
    wget \
    git \
    nodejs \
    npm \
    socat \
    novnc \
    websockify \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# install python deps
RUN pip3 install pyserial --break-system-packages

# install ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# copy luo_os source
WORKDIR /luo_os
COPY . .

# build the OS
RUN make clean && make

# copy agent
COPY agent/ /luo_os/agent/

# expose ports
# 5900 = VNC
# 6080 = noVNC web
# 11434 = Ollama API
# 7777 = luo_os serial bridge
EXPOSE 5900 6080 11434 7777

# supervisord config
COPY docker/supervisord.conf /etc/supervisor/conf.d/luoos.conf

# startup script
COPY docker/start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]
