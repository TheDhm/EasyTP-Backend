FROM ghcr.io/linuxserver/baseimage-kasmvnc:debianbookworm

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git cmake make g++ libsdl2-dev libsdl2-mixer-dev imagemagick \
        && rm -rf /var/lib/apt/lists/*

# Build SpaceCadetPinball from source
RUN cd /tmp && \
    git clone --depth 1 https://github.com/k4zmu2a/SpaceCadetPinball.git && \
    cd SpaceCadetPinball && mkdir build && cd build && \
    cmake .. && make -j$(nproc) && \
    mkdir -p /pinball && \
    cp /tmp/SpaceCadetPinball/bin/SpaceCadetPinball /pinball/ && \
    rm -rf /tmp/SpaceCadetPinball

# Get game data files
RUN cd /tmp && \
    git clone --depth 1 https://github.com/amamic1803/Full-Tilt-Pinball.git && \
    cp -r /tmp/Full-Tilt-Pinball/boards/3D\ Pinball\ for\ Windows\ -\ Space\ Cadet/* /pinball/ && \
    rm -rf /tmp/Full-Tilt-Pinball

# Configure autostart to launch pinball
RUN mkdir -p /defaults && \
    echo "/pinball/SpaceCadetPinball" > /defaults/autostart

# Configure desktop menu and wallpaper
COPY menu.xml /defaults/menu.xml
COPY wallpaper.jpg /tmp/wallpaper.jpg
RUN mkdir -p /usr/share/backgrounds && \
    convert /tmp/wallpaper.jpg /usr/share/backgrounds/bg_default.png && \
    rm /tmp/wallpaper.jpg

# Cleanup build dependencies
RUN apt-get remove -y git cmake make g++ imagemagick && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set port to 8080 to match existing setup
ENV CUSTOM_PORT=8080
# Force English locale
ENV LC_ALL=en_US.UTF-8

EXPOSE 8080