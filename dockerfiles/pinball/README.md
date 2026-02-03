# Space Cadet Pinball

Docker container running 3D Pinball for Windows - Space Cadet via noVNC.

## Credits

This container uses the following open source projects:

- **SpaceCadetPinball** - Decompilation/port of the game engine
  https://github.com/k4zmu2a/SpaceCadetPinball

- **Full-Tilt-Pinball** - Game data files
  https://github.com/amamic1803/Full-Tilt-Pinball

## Usage

```bash
docker build -t pinball .
docker run -e VNC_PW=yourpassword -p 8080:8080 pinball
```

Access via browser at `http://localhost:8080`