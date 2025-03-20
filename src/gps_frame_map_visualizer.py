#!/usr/bin/env python3
"""
GPS Street Map Visualizer for Argentina
--------------------------------------
This script reads GPS metadata from extracted frames and plots them precisely
on streets in an interactive map. It shows all four camera views for each GPS position.
Specifically designed for Ituzaingó/Morón area in Argentina.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import glob
from datetime import datetime
import json
import subprocess
import webbrowser
from typing import List, Dict, Tuple, Optional

try:
    import folium
    # Remove LatLngPopup import since it's not available in this version
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

try:
    from GPSPhoto import gpsphoto
    GPSPHOTO_AVAILABLE = True
except ImportError:
    GPSPHOTO_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GPSExtractor:
    """Extract GPS metadata from image files using GPSPhoto."""
    
    def __init__(self):
        """Initialize GPS metadata extractor."""
        if not GPSPHOTO_AVAILABLE:
            logger.error("GPSPhoto is not installed. Please run: pip install GPSPhoto")
            raise ImportError("GPSPhoto is required but not installed")
            
    def get_gps_data(self, image_path: str) -> Dict:
        """
        Extract GPS data from an image file using GPSPhoto.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dict: Dictionary with GPS data including Latitude and Longitude
        """
        try:
            gps_data = gpsphoto.getGPSData(image_path)
            return gps_data
        except Exception as e:
            logger.warning(f"Error getting GPS data for {image_path}: {e}")
            return {}
    
    def get_coordinates(self, image_path: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Get latitude and longitude from an image file.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Tuple[Optional[float], Optional[float]]: Latitude and longitude
        """
        gps_data = self.get_gps_data(image_path)
        
        lat = gps_data.get("Latitude")
        lon = gps_data.get("Longitude")
        
        # Ensure coordinates are for Argentina (specifically Buenos Aires area)
        if lat is not None and lon is not None:
            # Fix for Ituzaingó/Morón area (west of Buenos Aires)
            # Approximate bounding box for this region:
            # Latitude: -34.8 to -34.5
            # Longitude: -59.0 to -58.5
            
            in_buenos_aires_region = (-34.8 <= lat <= -34.5 and -59.0 <= lon <= -58.5)
            
            if not in_buenos_aires_region:
                # Try flipping signs
                if (-34.8 <= -lat <= -34.5 and -59.0 <= -lon <= -58.5):
                    logger.info(f"Flipping both coordinates: ({lat}, {lon}) → ({-lat}, {-lon})")
                    return -lat, -lon
                
                # Try flipping only latitude
                if (-34.8 <= -lat <= -34.5 and -59.0 <= lon <= -58.5):
                    logger.info(f"Flipping latitude: ({lat}, {lon}) → ({-lat}, {lon})")
                    return -lat, lon
                
                # Try flipping only longitude
                if (-34.8 <= lat <= -34.5 and -59.0 <= -lon <= -58.5):
                    logger.info(f"Flipping longitude: ({lat}, {lon}) → ({lat}, {-lon})")
                    return lat, -lon
                
                logger.warning(f"Coordinates ({lat}, {lon}) appear to be outside the expected region")
        
        return lat, lon


class StreetMapVisualizer:
    """Create interactive street maps from GPS coordinates."""
    
    def __init__(self):
        """Initialize map visualizer."""
        if not FOLIUM_AVAILABLE:
            logger.error("Folium is not installed. Please run: pip install folium")
            raise ImportError("Folium is required but not installed")
    
    def create_map(self, frame_data, output_path, title="GPS Street Map"):
        """
        Create an interactive street map showing GPS locations.
        
        Args:
            frame_data: Dict mapping frame numbers to tuples of (lat, lon, camera_paths)
            output_path: Path to save HTML map
            title: Map title
            
        Returns:
            str: Path to saved HTML map
        """
        # Filter out entries with missing coordinates
        valid_data = {
            frame_num: (lat, lon, cameras) 
            for frame_num, (lat, lon, cameras) in frame_data.items() 
            if lat is not None and lon is not None
        }
        
        if not valid_data:
            logger.error("No valid GPS data found")
            return None
        
        # Calculate center point of the map
        lats = [lat for lat, _, _ in valid_data.values()]
        lons = [lon for _, lon, _ in valid_data.values()]
        
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        center_point = [center_lat, center_lon]
        
        # Create map centered on the average coordinates with high zoom level
        m = folium.Map(
            location=center_point,
            zoom_start=19,  # High zoom level to see streets clearly
            control_scale=True,
            max_zoom=19,
            tiles='OpenStreetMap'  # Use OpenStreetMap for good street detail
        )
        
        # Remove LatLngPopup usage
        # Instead, add a custom JavaScript to show coordinates on click
        js_script = """
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            var map = document.querySelector('.folium-map');
            map.addEventListener('click', function(e) {
                console.log('Clicked at position:', e.latlng);
                // Display coordinates in a small div
                var coordsDiv = document.getElementById('coords-display');
                if (!coordsDiv) {
                    coordsDiv = document.createElement('div');
                    coordsDiv.id = 'coords-display';
                    coordsDiv.style.position = 'absolute';
                    coordsDiv.style.zIndex = '1000';
                    coordsDiv.style.backgroundColor = 'white';
                    coordsDiv.style.padding = '5px';
                    coordsDiv.style.border = '1px solid black';
                    coordsDiv.style.borderRadius = '3px';
                    coordsDiv.style.bottom = '10px';
                    coordsDiv.style.left = '10px';
                    document.body.appendChild(coordsDiv);
                }
                coordsDiv.innerHTML = 'Latitude: ' + e.latlng.lat.toFixed(6) + 
                                     '<br>Longitude: ' + e.latlng.lng.toFixed(6);
            });
        });
        </script>
        """
        
        # Add title
        title_html = f'''
            <h3 align="center" style="font-size:16px"><b>{title}</b></h3>
            <p align="center">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p align="center">Total locations: {len(valid_data)}</p>
            <p align="center">Center: {center_lat:.6f}, {center_lon:.6f}</p>
            {js_script}
        '''
        m.get_root().html.add_child(folium.Element(title_html))
        
        # Add markers for each frame (no clustering)
        for frame_num, (lat, lon, cameras) in sorted(valid_data.items()):
            # Create popup content with all four camera views
            popup_content = f"""
            <div style="text-align: center;">
                <h4>Frame {frame_num}</h4>
                <p>Coordinates: {lat:.6f}, {lon:.6f}</p>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 5px;">
            """
            
            # Add camera views to popup
            camera_labels = {
                'FD': 'Front Right',
                'FI': 'Front Left',
                'LD': 'Side Right',
                'LI': 'Side Left'
            }
            
            for camera_key, camera_path in cameras.items():
                camera_name = camera_labels.get(camera_key, camera_key)
                popup_content += f"""
                    <div style="margin: 5px;">
                        <p><strong>{camera_name}</strong></p>
                        <img src="file:///{os.path.abspath(camera_path)}" style="max-width: 150px; max-height: 150px;">
                    </div>
                """
                
            popup_content += """
                </div>
            </div>
            """
            
            # Add marker with popup
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_content, max_width=400),
                tooltip=f"Frame {frame_num}"
            ).add_to(m)
        
        # Add line showing the path
        points = [(lat, lon) for lat, lon, _ in 
                 [valid_data[frame] for frame in sorted(valid_data.keys())]]
        
        folium.PolyLine(
            points, 
            color='red',
            weight=3,
            opacity=0.7
        ).add_to(m)
        
        # Save map to HTML file
        m.save(output_path)
        logger.info(f"Map saved to {output_path}")
        
        return output_path


def get_camera_paths(input_folder):
    """
    Get paths to camera subfolders.
    
    Args:
        input_folder: Base input folder
        
    Returns:
        Dict: Mapping of camera codes to paths
    """
    camera_folders = {
        'FD': 'Imagenes_Frontal_Derecha',
        'FI': 'Imagenes_Frontal_Izquierda',
        'LD': 'Imagenes_Lateral_Derecha',
        'LI': 'Imagenes_Lateral_Izquierda'
    }
    
    result = {}
    for code, folder in camera_folders.items():
        path = os.path.join(input_folder, folder)
        if os.path.isdir(path):
            result[code] = path
            logger.info(f"Found camera folder: {code} at {path}")
        else:
            logger.warning(f"Camera folder not found: {path}")
            
    return result


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='GPS Street Map Visualizer for Ituzaingó/Morón area')
    parser.add_argument('input_folder', help='Path to folder containing extracted frames')
    parser.add_argument('--output', '-o', help='Path to save HTML map (default: street_map.html)')
    parser.add_argument('--title', '-t', default='Ituzaingó/Morón Street Map', help='Map title')
    parser.add_argument('--open', action='store_true', help='Open map in browser after creation')
    
    return parser.parse_args()


def main():
    """Main entry point for the application."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Check for required libraries
    if not GPSPHOTO_AVAILABLE:
        logger.error("GPSPhoto is not installed. Please run: pip install GPSPhoto")
        return 1
        
    if not FOLIUM_AVAILABLE:
        logger.error("Folium is not installed. Please run: pip install folium")
        return 1
    
    # Determine input and output paths
    input_folder = args.input_folder
    
    # Check if input folder exists
    if not os.path.isdir(input_folder):
        logger.error(f"Input folder not found: {input_folder}")
        return 1
        
    # Get camera paths
    camera_paths = get_camera_paths(input_folder)
    if not camera_paths:
        logger.error(f"No camera folders found in {input_folder}")
        return 1
        
    # Determine output path
    output_path = args.output
    if not output_path:
        output_path = os.path.join(os.getcwd(), "street_map.html")
        
    # Create GPS extractor and map visualizer
    gps_extractor = GPSExtractor()
    map_visualizer = StreetMapVisualizer()
    
    # Process images from the front-right camera (reference camera)
    reference_camera = 'FD'
    if reference_camera not in camera_paths:
        # Fall back to first available camera
        reference_camera = list(camera_paths.keys())[0]
        
    reference_path = camera_paths[reference_camera]
    logger.info(f"Using {reference_camera} as reference camera from {reference_path}")
    
    # Get list of image files from reference camera
    image_files = []
    for ext in ['jpg', 'jpeg', 'png']:
        image_files.extend(glob.glob(os.path.join(reference_path, f"*.{ext}")))
        image_files.extend(glob.glob(os.path.join(reference_path, f"*.{ext.upper()}")))
        
    if not image_files:
        logger.error(f"No image files found in reference camera folder: {reference_path}")
        return 1
        
    logger.info(f"Processing {len(image_files)} image files...")
    
    # Group by frame number and gather all camera views
    frame_data = {}
    for i, image_path in enumerate(sorted(image_files)):
        if i % 10 == 0:  # Log progress every 10 images
            logger.info(f"Processing image {i+1}/{len(image_files)}: {os.path.basename(image_path)}")
            
        # Extract frame number from filename
        filename = os.path.basename(image_path)
        frame_num = os.path.splitext(filename)[0]
        
        # Find corresponding images from other cameras
        camera_images = {reference_camera: image_path}
        for camera_code, camera_path in camera_paths.items():
            if camera_code == reference_camera:
                continue
                
            # Look for matching frame in this camera
            other_path = os.path.join(camera_path, filename)
            if os.path.exists(other_path):
                camera_images[camera_code] = other_path
                
        # Check if we have images from all cameras
        if len(camera_images) == len(camera_paths):
            # Extract GPS data from reference image
            lat, lon = gps_extractor.get_coordinates(image_path)
            
            if lat is not None and lon is not None:
                frame_data[frame_num] = (lat, lon, camera_images)
                
    logger.info(f"Found {len(frame_data)} locations with all camera views")
    
    # Create street map
    map_path = map_visualizer.create_map(
        frame_data,
        output_path,
        title=args.title
    )
    
    if map_path and args.open:
        # Open map in browser
        logger.info(f"Opening map in browser: {map_path}")
        webbrowser.open('file://' + os.path.abspath(map_path))
        
    return 0


if __name__ == "__main__":
    sys.exit(main())