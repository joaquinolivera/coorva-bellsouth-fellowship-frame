# Fellowship of the Frame

A comprehensive video processing system that extracts frames from multi-camera vehicle setups with GPS synchronization and generates interactive map visualizations.

## Project Overview

This project processes video footage from a four-camera vehicle setup (front right/left, side right/left), extracts frames at specified intervals, embeds GPS data from video metadata, and generates interactive map visualizations. It is specifically designed for the Ituzaingó/Morón area in Argentina and handles camera synchronization, GPS tagging, and visualization of collected data.

## Key Features

- Supports four-camera vehicle setups.
- Manual or automatic camera synchronization.
- Configurable frame extraction rates (2, 4, 5, or 10 fps).
- GPS metadata extraction and embedding into frames.
- Interactive street map visualizations for camera views.
- Automatic coordinate correction for the Ituzaingó/Morón area.

## Directory Structure

```
fellowship_of_the_frame/
├── data/
│   ├── Videos/
│   │   ├── FD/  # Front Right Camera
│   │   ├── FI/  # Front Left Camera
│   │   ├── LD/  # Side Right Camera
│   │   └── LI/  # Side Left Camera
│   └── Fotos/
│       └── [output_folder]/
│           ├── Imagenes_Frontal_Derecha/
│           ├── Imagenes_Frontal_Izquierda/
│           ├── Imagenes_Lateral_Derecha/
│           └── Imagenes_Lateral_Izquierda/
├── src/
│   ├── auto_sync_videos.py
│   ├── gps_frame_map_visualizer.py
│   └── check_dir_structure.py
├── .gitignore
├── pyproject.toml
├── requirements.in
├── requirements.txt
├── setup.cfg
└── README.md
```

## Prerequisites

- Python 3.8 or later
- ExifTool ([Download](https://exiftool.org/))
- Git

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/joaquinolivera/coorva-bellsouth-fellowship-frame.git
cd fellowship_of_the_frame
```

### 2. Create and activate a virtual environment

```bash
python -m venv fellow-env
# Windows
fellow-env\Scripts\activate
# macOS/Linux
source fellow-env/bin/activate
```

### 3. Install `pip-tools` (if not already installed)

```bash
pip install pip-tools
```

### 4. Generate dependencies

Use `pip-compile` to generate `requirements.txt` from `requirements.in`:

```bash
pip-compile requirements.in
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

### 6. Verify project setup

```bash
python src/check_dir_structure.py
```

### 7. Create required directories

```bash
mkdir -p data/Videos/{FD,FI,LD,LI} data/Fotos
```

## Usage

### Check Directory Structure

```bash
python src/check_dir_structure.py
```

### Automatic Video Frame Extraction

```bash
python src/auto_sync_videos.py data/Videos/[video_folder] data/Fotos/[output_folder] --start-frame [frames] --fps [rate]

# Example:
python src/auto_sync_videos.py data/Videos/Camino_8 data/Fotos/C8 --start-frame 500 --fps 5
```

Parameters:
- `--start-frame`: Frames to skip initially.
- `--fps`: Frames per second (2, 4, 5, 10).

### GPS Map Visualization

Generate an interactive map from extracted GPS-tagged frames:

```bash
python src/gps_frame_map_visualizer.py data/Fotos/[output_folder] --open

# Example:
python src/gps_frame_map_visualizer.py data/Fotos/C8 --open
```

Optional parameters:
- `-o`: Specify HTML output (default: street_map.html)
- `-t`: Map title
- `--open`: Open automatically in browser

## Technical Details

- Input videos: 60 fps
- GPS data frequency: 10 locations/sec
- Output rates: 2, 4, 5, or 10 fps
- Output format: JPG with GPS EXIF data
- Resolution: 640x640 pixels

### Frame Extraction Workflow

1. Read GPS metadata with ExifTool.
2. Extract frames at specified fps.
3. Match frames with GPS data.
4. Resize to 640x640.
5. Embed GPS EXIF metadata.

### GPS Map Workflow

1. Extract GPS data from frames.
2. Correct local coordinates.
3. Generate interactive HTML map.
4. Display all camera views.

## Troubleshooting

- **Missing ExifTool**:

```bash
exiftool -ver
```

- **Folium or GPSPhoto Import Errors**:

```bash
pip install folium GPSPhoto
```

- **No GPS Data**: Ensure your videos have GPS metadata:

```bash
exiftool -G3 -s -GPS* path/to/video.mp4
```

## Contributing

1. Fork the repository
2. Create a branch (`git checkout -b feature/your-feature`)
3. Commit changes (`git commit -m 'Your feature description'`)
4. Push changes (`git push origin feature/your-feature`)
5. Open a pull request

## License

Licensed under the MIT License.

## Acknowledgements

- [OpenCV](https://opencv.org/) - Video processing
- [ExifTool](https://exiftool.org/) - Metadata extraction
- [GPSPhoto](https://pypi.org/project/GPSPhoto/) - GPS tagging
- [Folium](https://python-visualization.github.io/folium/) - Map visualization

