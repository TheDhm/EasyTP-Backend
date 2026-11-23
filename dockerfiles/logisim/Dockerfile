FROM debian:bookworm-slim
ENV DEBIAN_FRONTEND=noninteractive

# rebuild

# Install all required packages in a single layer and clean up
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        # Core VNC and desktop components
        openbox tigervnc-standalone-server tigervnc-common supervisor gosu \
        # VNC password utility
        tigervnc-tools \
        # Java runtime for Logisim
        default-jre \
        # Essential utilities
        wget ca-certificates \
        # noVNC requirements
        python3-websockify \
        # Desktop components
        tint2 feh thunar dbus-x11 xdg-utils \
        # Clean up
        && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
        && apt-get clean

# Create directories and download Logisim in one layer
RUN mkdir -p /logisim /data/myData /data/readonly /home/.vnc /home/wallpaper /usr/share/desktop-directories && \
    wget -O /logisim/logisim-generic-2.7.1.jar https://sourceforge.net/projects/circuit/files/2.7.x/2.7.1/logisim-generic-2.7.1.jar && \
    echo "362a78c12ad18c203fed868872c4a01cd9c12141379d92e892bbe2c37e627bc2  /logisim/logisim-generic-2.7.1.jar" | sha256sum -c - && \
    groupadd --gid 1000 app && \
    useradd --home-dir /data --shell /bin/bash --uid 1000 --gid 1000 app

# Download and install noVNC 1.6.0
RUN wget -O /tmp/novnc.tar.gz https://github.com/novnc/noVNC/archive/refs/tags/v1.6.0.tar.gz && \
    echo "5066103959ef4e9b10f37e5a148627360dd8414e4cf8a7db92bdbd022e728aaa  /tmp/novnc.tar.gz" | sha256sum -c - && \
    mkdir -p /usr/share/novnc && \
    tar -xzf /tmp/novnc.tar.gz -C /usr/share/novnc --strip-components=1 && \
    rm /tmp/novnc.tar.gz

# Copy files
COPY menu.xml /etc/xdg/openbox/
COPY supervisord.conf /etc/
COPY wallpaper.jpg /home/wallpaper/wallpaper.jpg

EXPOSE 8080
VOLUME /data

CMD ["sh", "-c", "chown app:app /data /dev/stdout && echo ${VNC_PW} | tigervncpasswd -f > /home/.vnc/passwd && exec gosu app supervisord"]