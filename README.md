# Fellowship of the Frame

A comprehensive video processing system that extracts frames from multi-camera vehicle setups with GPS synchronization and generates interactive map visualizations.

## Project Overview

This project processes video footage from a four-camera vehicle setup (front right/left, side right/left), extracts frames at specified intervals, embeds GPS data from video metadata, and generates interactive map visualizations. The system is specifically designed for the Ituzaingó/Morón area in Argentina and handles camera synchronization, GPS tagging, and visualization of the collected data.

## Key Features

- Process videos from four-camera vehicle setups
- Manual or automatic camera synchronization options
- Extract frames at configurable frame rates (2, 4, 5, or 10 fps)
- Extract and embed GPS metadata in frame images
- Generate interactive street map visualizations showing all camera views
- Automatic coordinate correction for Ituzaingó/Morón area (Argentina)

## Directory Structure

```
fellowship_of_the_frame/
├── data/
│   ├── Videos/
│   │   ├── FD/  (Front Right Camera Videos)
│   │   ├── FI/  (Front Left Camera Videos)
│   │   ├── LD/  (Side Right Camera Videos)
│   │   └── LI/  (Side Left Camera Videos)
│   └── Fotos/
│       └── [output_folder]/
│           ├── Imagenes_Frontal_Derecha/
│           ├── Imagenes_Frontal_Izquierda/
│           ├── Imagenes_Lateral_Derecha/
│           └── Imagenes_Lateral_Izquierda/
├── src/
│   ├── auto_sync_videos.py
│   ├── gps_frame_map_visualizer.py
│   ├── check_dir_structure.py
├── .gitignore
├── pyproject.toml
├── requirements.in
├── requirements.txt
├── setup.cfg
└── README.md
```

## Prerequisites

- Python 3.8 or later
- ExifTool installed on your system ([Download from official site](https://exiftool.org/))
- Git (for version control)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/fellowship_of_the_frame.git
cd fellowship_of_the_frame
```

2. Create and activate a virtual environment:
```bash
python -m venv fellow-env
# On Windows
fellow-env\Scripts\activate
# On macOS/Linux
source fellow-env/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Verify your setup:
```bash
python src/check_dir_structure.py
```

5. Create the required directories if they don't exist:
```bash
mkdir -p data/Videos/{FD,FI,LD,LI} data/Fotos
```

## Usage Guide

### 1. Check Directory Structure

First, verify that your project directory structure is set up correctly:

```bash
python src/check_dir_structure.py
```

This will check for the required directories and report any issues.

### 2. Automatic Video Frame Extraction

Use the automatic extraction script to process videos and extract frames:

```bash
python src/auto_sync_videos.py data/Videos/[video_folder] data/Fotos/[output_folder] --start-frame [frames] --fps [rate]

# Example:
python src/auto_sync_videos.py data/Videos/Camino_8 data/Fotos/C8 --start-frame 500 --fps 5
```

Parameters:
- `video_folder`: Path to folder containing camera subfolders
- `output_folder`: Path to output folder for extracted frames
- `--start-frame`: Number of frames to skip from the beginning
- `--fps`: Frames per second to extract (options: 2, 4, 5, or 10 fps)

### 3. GPS Map Visualization

Create an interactive map from the extracted frames with GPS data:

```bash
python src/gps_frame_map_visualizer.py data/Fotos/[output_folder] --open

# Example:
python src/gps_frame_map_visualizer.py data/Fotos/C8 --open
```

Options:
- `--output`, `-o`: Specify output HTML file path (default: street_map.html)
- `--title`, `-t`: Set map title (default: "Ituzaingó/Morón Street Map")
- `--open`: Automatically open the generated map in the default browser

## Technical Details

- Input videos: 60 fps
- GPS data frequency: 10 locations/second
- Available output rates: 2, 4, 5, or 10 fps
- Output image format: JPG with embedded GPS EXIF data
- Default output resolution: 640x640 pixels

### Frame Extraction Process

The frame extraction process works by:
1. Reading GPS metadata from video files using ExifTool
2. Sampling frames at intervals based on the requested output fps
3. Automatically matching frames with corresponding GPS data
4. Resizing frames to 640x640 square images
5. Embedding GPS data in the output images

### GPS Map Visualization

The map visualization:
1. Reads GPS data from extracted frames
2. Corrects coordinates for the Ituzaingó/Morón area if needed
3. Creates an interactive HTML map with all camera views
4. Draws a path line connecting all GPS points
5. Shows camera views from all four cameras in popups

## Troubleshooting

### Common Issues

1. **Missing ExifTool**: Ensure ExifTool is installed and available in your PATH
   ```bash
   # Check if ExifTool is installed
   exiftool -ver
   ```

2. **Folium Import Error**: Make sure Folium is installed correctly
   ```bash
   pip install folium
   ```

3. **GPSPhoto Import Error**: Install the GPSPhoto package
   ```bash
   pip install GPSPhoto
   ```

4. **GPS Data Not Found**: Verify your videos contain GPS metadata
   ```bash
   # Check if a video contains GPS data
   exiftool -G3 -s -GPS* path/to/video.mp4
   ```

5. **Images Not Showing in Map**: Check browser security settings for local file access

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [OpenCV](https://opencv.org/) for video processing
- [ExifTool](https://exiftool.org/) for metadata extraction
- [GPSPhoto](https://pypi.org/project/GPSPhoto/) for GPS tagging
- [Folium](https://python-visualization.github.io/folium/) for map visualization