FROM debian:bookworm-slim
ENV DEBIAN_FRONTEND=noninteractive

# Install all required packages in a single layer and clean up
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        # Core VNC and desktop components
        openbox tigervnc-standalone-server tigervnc-common supervisor gosu \
        # VNC password utility
        tigervnc-tools \
        # Build dependencies
        git cmake make g++ \
        # Runtime dependencies for SpaceCadetPinball
        libsdl2-2.0-0 libsdl2-mixer-2.0-0 \
        # Build dependencies for SpaceCadetPinball
        libsdl2-dev libsdl2-mixer-dev \
        # Essential utilities
        wget ca-certificates \
        # noVNC requirements
        python3-websockify \
        # Desktop components
        tint2 feh thunar dbus-x11 xdg-utils \
        && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
        && apt-get clean

# Create directories and user
RUN mkdir -p /pinball /data/myData /data/readonly /home/.vnc /home/wallpaper /usr/share/desktop-directories && \
    groupadd --gid 1000 app && \
    useradd --home-dir /data --shell /bin/bash --uid 1000 --gid 1000 app

# Build SpaceCadetPinball from source
RUN cd /tmp && \
    git clone --depth 1 https://github.com/k4zmu2a/SpaceCadetPinball.git && \
    cd SpaceCadetPinball && mkdir build && cd build && \
    cmake .. && make -j$(nproc) && \
    cp /tmp/SpaceCadetPinball/bin/SpaceCadetPinball /pinball/ && \
    rm -rf /tmp/SpaceCadetPinball

# Get game data files
RUN cd /tmp && \
    git clone --depth 1 https://github.com/amamic1803/Full-Tilt-Pinball.git && \
    cp -r "/tmp/Full-Tilt-Pinball/boards/3D Pinball for Windows - Space Cadet"/* /pinball/ && \
    rm -rf /tmp/Full-Tilt-Pinball

# Download and install noVNC 1.6.0
RUN wget -O /tmp/novnc.tar.gz https://github.com/novnc/noVNC/archive/refs/tags/v1.6.0.tar.gz && \
    mkdir -p /usr/share/novnc && \
    tar -xzf /tmp/novnc.tar.gz -C /usr/share/novnc --strip-components=1 && \
    rm /tmp/novnc.tar.gz

# Cleanup build dependencies
RUN apt-get remove -y git cmake make g++ libsdl2-dev libsdl2-mixer-dev && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy files
COPY menu.xml /etc/xdg/openbox/
COPY supervisord.conf /etc/
COPY wallpaper.jpg /home/wallpaper/wallpaper.jpg

EXPOSE 8080
VOLUME /data

CMD ["sh", "-c", "chown app:app /data /dev/stdout && echo ${VNC_PW} | tigervncpasswd -f > /home/.vnc/passwd && exec gosu app supervisord"]