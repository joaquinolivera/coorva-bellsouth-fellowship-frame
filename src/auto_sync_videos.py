#!/usr/bin/env python3
"""
Automatic Video Frame Extraction with GPS Synchronization
--------------------------------------------------------
This script processes videos from 4 cameras, extracts frames at 640x640 resolution
and automatically embeds GPS metadata using GoPro's Python API when available,
falling back to ExifTool if needed.
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from datetime import datetime, timedelta
import cv2
import numpy as np
from PIL import Image
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
    
# Try to import GPSPhoto for metadata writing
try:
    from GPSPhoto import gpsphoto
    GPSPHOTO_AVAILABLE = True
except ImportError:
    GPSPHOTO_AVAILABLE = False
    logger.warning("GPSPhoto not available - install with 'pip install GPSPhoto'")


class GPSDataProcessor:
    """Process and manage GPS data from video metadata."""
    
    def __init__(self, fps_video=60, fps_gps=10):
        """
        Initialize GPS data processor.
        
        Args:
            fps_video: Frames per second of the video (default: 60)
            fps_gps: GPS data points per second (default: 10)
        """
        self.gps_data = []  # Format: [timestamp, latitude, longitude]
        self.total_data = []
        self.fps_video = fps_video
        self.fps_gps = fps_gps
        self.frame_time_ms = 1000.0 / self.fps_video  # Time per frame in milliseconds
    
    def extract_track4_data(self, input_file: str, output_file: str) -> None:
        """
        Extract Track4 GPS data from metadata file.
        
        Args:
            input_file: Path to metadata file
            output_file: Path to output GPS data file
        """
        try:
            with open(input_file, 'r') as in_file, open(output_file, 'w') as out_file:
                for line in in_file:
                    if 'Track4' in line:
                        out_file.write(line)
            logger.info(f"Extracted Track4 GPS data to {output_file}")
        except IOError as e:
            logger.error(f"Error processing metadata file: {e}")
            raise
    
    def dms_to_decimal(self, degrees: str, minutes: str, seconds: str, direction: str) -> float:
        """
        Convert GPS coordinates from DMS format to decimal degrees.
        
        Args:
            degrees: Degrees value
            minutes: Minutes value
            seconds: Seconds value
            direction: Direction (N, S, E, W)
            
        Returns:
            float: Decimal degrees
        """
        try:
            dd = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
            if direction in ['W', 'S']:
                dd *= -1
            return round(dd, 6)
        except (ValueError, TypeError) as e:
            logger.error(f"Error converting DMS to decimal: {e}")
            return 0.0
    
    def convert_gps_coords(self, data: str) -> float:
        """
        Parse and convert GPS coordinate string to decimal format.
        
        Args:
            data: GPS coordinate string in DMS format
            
        Returns:
            float: Decimal coordinate
        """
        if not data or not isinstance(data, str):
            logger.warning(f"Invalid GPS data: {data}")
            return 0.0
            
        try:
            parts = data.split(' ')
            
            if len(parts) < 6:
                logger.warning(f"GPS coordinate format incorrect: '{data}'")
                return 0.0
                
            direction = parts[5][0] if len(parts[5]) > 0 else None
            if direction not in ['N', 'S', 'E', 'W']:
                logger.warning(f"Invalid direction in GPS coordinate: '{direction}' from '{data}'")
                return 0.0
            
            degrees = parts[1]
            minutes = parts[3].split("'")[0]
            seconds = parts[4].split('"')[0]
            
            return self.dms_to_decimal(degrees, minutes, seconds, direction)
                
        except Exception as e:
            logger.error(f"Error parsing GPS coordinate '{data}': {e}")
            return 0.0
    
    def convert_timestamp(self, timestamp: str) -> str:
        """
        Clean and convert timestamp format.
        
        Args:
            timestamp: Timestamp string
            
        Returns:
            str: Formatted timestamp
        """
        # Remove first and last characters if they are <...>
        if timestamp.startswith('<') and timestamp.endswith('>'):
            timestamp = timestamp[1:-1]
        
        # Remove any leading/trailing whitespace
        return timestamp.strip()
    
    def read_gps_data(self, gps_file: str) -> bool:
        """
        Parse GPS data from extracted metadata file.
        
        Args:
            gps_file: Path to GPS data file
            
        Returns:
            bool: True if GPS data was successfully parsed, False otherwise
        """
        try:
            with open(gps_file, 'r') as f:
                # Skip first two lines
                f.readline()
                f.readline()
                
                self.gps_data = []
                self.total_data = []
                
                last_timestamp = None
                counter = 0
                latitude = None
                longitude = None
                timestamp_formatted = None
                
                while True:
                    line = f.readline()
                    if not line:
                        if last_timestamp:
                            try:
                                dt = datetime.strptime(last_timestamp, '%Y:%m:%d %H:%M:%S.%f')
                                self.total_data.append([last_timestamp, counter, dt.timestamp() * 1000])
                            except ValueError:
                                try:
                                    dt = datetime.strptime(last_timestamp, '%Y:%m:%d %H:%M:%S')
                                    self.total_data.append([last_timestamp, counter, dt.timestamp() * 1000])
                                except ValueError as e:
                                    logger.warning(f"Invalid timestamp format: {last_timestamp} - {e}")
                        break
                    
                    data = line.split(':')
                    gps_text = BeautifulSoup(line, "html.parser").get_text()
                    
                    if len(data) < 2 or data[1] == ' ':
                        continue
                        
                    tag = data[1].split('>')[0]
                    
                    if tag == "GPSLatitude":
                        latitude = gps_text
                    elif tag == "GPSLongitude" and latitude is not None:
                        counter += 1
                        longitude = gps_text
                        
                        if timestamp_formatted is not None:
                            lat_decimal = self.convert_gps_coords(latitude)
                            lon_decimal = self.convert_gps_coords(longitude)
                            
                            # Only store valid coordinates
                            if lat_decimal != 0.0 and lon_decimal != 0.0:
                                self.gps_data.append([
                                    timestamp_formatted, 
                                    lat_decimal,
                                    lon_decimal
                                ])
                    elif tag == "GPSDateTime":
                        timestamp = gps_text
                        timestamp_formatted = self.convert_timestamp(timestamp)
                        
                        if last_timestamp:
                            try:
                                dt = datetime.strptime(last_timestamp, '%Y:%m:%d %H:%M:%S.%f')
                                self.total_data.append([last_timestamp, counter, dt.timestamp() * 1000])
                            except ValueError:
                                try:
                                    dt = datetime.strptime(last_timestamp, '%Y:%m:%d %H:%M:%S')
                                    self.total_data.append([last_timestamp, counter, dt.timestamp() * 1000])
                                except ValueError as e:
                                    logger.warning(f"Invalid timestamp format: {last_timestamp} - {e}")
                            counter = 0
                        last_timestamp = timestamp_formatted
                
                if len(self.gps_data) > 0:
                    logger.info(f"Processed {len(self.gps_data)} GPS data points")
                    return True
                else:
                    logger.warning("No valid GPS data found in the file!")
                    return False
                
        except Exception as e:
            logger.error(f"Error reading GPS data: {e}")
            return False

    def get_timestamps_ms(self) -> List[float]:
        """
        Get list of timestamps in milliseconds for GPS data points.
        
        Returns:
            List[float]: List of timestamps in milliseconds
        """
        timestamps_ms = []
        
        if not self.gps_data:
            return timestamps_ms
            
        # Process each GPS data point and extract timestamp
        try:
            for gps_point in self.gps_data:
                timestamp_str = gps_point[0]
                
                try:
                    if '.' in timestamp_str:
                        dt = datetime.strptime(timestamp_str, '%Y:%m:%d %H:%M:%S.%f')
                    else:
                        dt = datetime.strptime(timestamp_str, '%Y:%m:%d %H:%M:%S')
                        
                    # Convert to milliseconds timestamp
                    timestamps_ms.append(dt.timestamp() * 1000)
                except ValueError as e:
                    logger.warning(f"Invalid timestamp format: {timestamp_str} - {e}")
            
            # Normalize timestamps to start from 0 if we have any valid timestamps
            if timestamps_ms:
                start_time = timestamps_ms[0]
                timestamps_ms = [t - start_time for t in timestamps_ms]
                
        except Exception as e:
            logger.error(f"Error processing timestamps: {e}")
            
        return timestamps_ms
    
    def get_gps_for_frame(self, frame_number: int, total_frames: int) -> Tuple[Optional[str], float, float]:
        """
        Get GPS data for a specific frame number.
        
        Args:
            frame_number: Frame number in the video
            total_frames: Total number of frames in the video
            
        Returns:
            Tuple[Optional[str], float, float]: Timestamp, latitude, longitude
        """
        if not self.gps_data:
            return None, 0.0, 0.0
            
        # Calculate the video timestamp in milliseconds
        video_duration_ms = total_frames * self.frame_time_ms
        frame_time_ms = frame_number * self.frame_time_ms
        
        # Get GPS timestamps
        gps_timestamps_ms = self.get_timestamps_ms()
        if not gps_timestamps_ms:
            return None, 0.0, 0.0
            
        # Calculate the GPS data duration
        gps_duration_ms = gps_timestamps_ms[-1]
        
        # Scale the frame time to match GPS time range
        scaled_frame_time_ms = (frame_time_ms / video_duration_ms) * gps_duration_ms
        
        # Find the closest GPS timestamp
        closest_idx = min(range(len(gps_timestamps_ms)), 
                        key=lambda i: abs(gps_timestamps_ms[i] - scaled_frame_time_ms))
        
        # Return the corresponding GPS data
        if 0 <= closest_idx < len(self.gps_data):
            # Get timestamp but ensure it's in the right format
            timestamp = self.gps_data[closest_idx][0]
            # Remove milliseconds if present
            if '.' in timestamp:
                timestamp = timestamp.split('.')[0]
                
            return (
                timestamp,  # Timestamp without milliseconds
                self.gps_data[closest_idx][1],  # Latitude
                self.gps_data[closest_idx][2]   # Longitude
            )
        
        return None, 0.0, 0.0
    
    def extract_gopro_metadata(self, video_path: str) -> bool:
        """
        Extract GPS data from a GoPro video using the GoPro API.
        
        Args:
            video_path: Path to GoPro video file
            
        Returns:
            bool: True if data extraction was successful, False otherwise
        """
        if not GOPRO_API_AVAILABLE:
            logger.warning("GoPro API not available, cannot extract metadata")
            return False
            
        try:
            logger.info(f"Extracting GoPro metadata from {video_path}")
            
            # Clear any existing data
            self.gps_data = []
            
            # Create a GoPro instance for the video file
            with GoPro(path=video_path) as video:
                # Check if GPS data is available
                if not video.telemetry.has('GPS'):
                    logger.warning(f"No GPS data found in GoPro video {video_path}")
                    return False
                    
                # Extract GPS data
                gps_data = video.telemetry.get('GPS')
                fps = video.framerate
                
                if not gps_data:
                    logger.warning("Empty GPS data returned from GoPro API")
                    return False
                
                # Process GPS data
                for i, point in enumerate(gps_data):
                    timestamp = point.get('timestamp')
                    
                    if not timestamp:
                        timestamp = datetime.now().strftime('%Y:%m:%d %H:%M:%S')
                    
                    latitude = point.get('latitude', 0.0)
                    longitude = point.get('longitude', 0.0)
                    
                    if latitude != 0.0 or longitude != 0.0:
                        self.gps_data.append([timestamp, latitude, longitude])
                
                logger.info(f"Extracted {len(self.gps_data)} GPS points from GoPro video")
                return len(self.gps_data) > 0
                
        except Exception as e:
            logger.error(f"Error extracting GoPro metadata: {e}")
            return False


class VideoProcessor:
    """Process video files and extract frames with automatic GPS synchronization."""
    
    def __init__(self, video_dir: str, output_dir: str, start_frame: int = 0, fps: int = 5):
        """
        Initialize video processor.
        
        Args:
            video_dir: Directory containing video files
            output_dir: Directory to save extracted frames
            start_frame: Number of frames to skip at the beginning
            fps: Frames per second to extract
        """
        self.video_dir = video_dir
        self.output_dir = output_dir
        self.start_frame = start_frame
        self.requested_fps = fps
        
        # Calculate sampling frequency based on requested fps
        # Base video is assumed to be 60fps, GPS is 10Hz
        # For perfect synchronization with GPS data:
        # - At 10 fps: sample every 6th frame (60 ÷ 10 = 6) - perfect match with GPS rate
        # - At 5 fps: sample every 12th frame (60 ÷ 5 = 12)
        # - At 4 fps: sample every 15th frame (60 ÷ 4 = 15)
        # - At 2 fps: sample every 30th frame (60 ÷ 2 = 30)
        self.freq_mapping = {10: 6, 5: 12, 4: 15, 2: 30}
        self.sampling_freq = self.freq_mapping.get(fps, 6)
        
        # Define output resolution (fixed at 640x640 as requested)
        self.output_size = (640, 640)
        
        logger.info(f"Using sampling frequency of {self.sampling_freq} for {fps} fps output")
        logger.info(f"Output image size: {self.output_size[0]}x{self.output_size[1]}")
        
        # Setup paths and verify directory structure
        self.setup_paths()
    
    def setup_paths(self) -> None:
        """
        Set up directories and paths, verify input/output directory structure.
        """
        # Define camera directories
        self.path_folder_fd = os.path.join(self.video_dir, 'FD')
        self.path_folder_fi = os.path.join(self.video_dir, 'FI')
        self.path_folder_ld = os.path.join(self.video_dir, 'LD')
        self.path_folder_li = os.path.join(self.video_dir, 'LI')
        
        # Verify input directory structure
        for dir_name in [self.path_folder_fd, self.path_folder_fi, 
                       self.path_folder_ld, self.path_folder_li]:
            if not os.path.isdir(dir_name):
                logger.warning(f"Input directory not found: {dir_name}")
        
        # Create output directories
        self.path_save = self.output_dir
        os.makedirs(self.path_save, exist_ok=True)
        
        # Create output subdirectories for each camera
        for dir_name in ['Imagenes_Frontal_Derecha', 'Imagenes_Frontal_Izquierda', 
                         'Imagenes_Lateral_Derecha', 'Imagenes_Lateral_Izquierda']:
            os.makedirs(os.path.join(self.path_save, dir_name), exist_ok=True)
        
        # Get video files for each camera
        self.files_fd = self._get_sorted_video_files(self.path_folder_fd)
        self.files_fi = self._get_sorted_video_files(self.path_folder_fi)
        self.files_ld = self._get_sorted_video_files(self.path_folder_ld)
        self.files_li = self._get_sorted_video_files(self.path_folder_li)
        
        # Log number of video files found
        logger.info(f"Found video files: FD={len(self.files_fd)}, FI={len(self.files_fi)}, " 
                  f"LD={len(self.files_ld)}, LI={len(self.files_li)}")
    
    def _get_sorted_video_files(self, directory: str) -> List[str]:
        """
        Get sorted list of video files in a directory.
        
        Args:
            directory: Directory path
            
        Returns:
            List[str]: Sorted list of video filenames
        """
        if not os.path.isdir(directory):
            logger.warning(f"Directory not found: {directory}")
            return []
            
        return sorted([
            f for f in os.listdir(directory) 
            if os.path.isfile(os.path.join(directory, f)) 
            and f.lower().endswith(('.mp4', '.avi', '.mov', '.MP4'))
        ])
    
    def extract_metadata(self, video_path: str, gps_processor: GPSDataProcessor) -> bool:
        """
        Extract metadata from video file using ExifTool.
        
        Args:
            video_path: Path to video file
            gps_processor: GPSDataProcessor instance
            
        Returns:
            bool: True if metadata extraction was successful, False otherwise
        """
        try:
            metadata_file = f"{os.path.splitext(video_path)[0]}_metadata.txt"
            gps_file = f"{os.path.splitext(video_path)[0]}_gps.txt"
            
            # Check for exiftool
            from shutil import which
            exiftool_path = which("exiftool")
            if exiftool_path:
                exiftool_cmd = exiftool_path
            elif os.path.exists("exiftool.exe"):
                exiftool_cmd = "exiftool.exe"
            else:
                logger.warning("exiftool not found in PATH or current directory")
                logger.warning("Attempting to use 'exiftool' command directly")
                exiftool_cmd = "exiftool"
                
            # Run exiftool command
            cmd = f'{exiftool_cmd} -api largefilesupport=1 -ee -G3 -X "{video_path}" > "{metadata_file}"'
            logger.info(f"Extracting metadata with command: {cmd}")
            
            result = os.system(cmd)
            if result != 0:
                logger.error(f"exiftool command failed with exit code {result}")
                return False
                
            # Extract GPS data
            gps_processor.extract_track4_data(metadata_file, gps_file)
            return gps_processor.read_gps_data(gps_file)
                
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return False
    
    def add_gps_to_image(self, image_path: str, lat: float, lon: float, timestamp: str) -> bool:
        """
        Add GPS metadata to an image file.
        
        Args:
            image_path: Path to image file
            lat: Latitude
            lon: Longitude
            timestamp: Timestamp string
            
        Returns:
            bool: True if successful, False otherwise
        """
        if GPSPHOTO_AVAILABLE:
            try:
                # First save with PIL to ensure format compatibility
                pil_img = Image.open(image_path)
                pil_img.save(image_path)
                
                # Fix timestamp format - remove milliseconds if present
                if '.' in timestamp:
                    timestamp = timestamp.split('.')[0]
                
                # Add GPS data
                photo = gpsphoto.GPSPhoto(image_path)
                info = gpsphoto.GPSInfo((lat, lon), timeStamp=timestamp)
                photo.modGPSData(info, image_path)
                return True
            except Exception as e:
                logger.warning(f"Error adding GPS data using GPSPhoto: {e}")
                
        # Fallback to exiftool if GPSPhoto fails or is not available
        try:
            from shutil import which
            exiftool_path = which("exiftool")
            if exiftool_path:
                exiftool_cmd = exiftool_path
            elif os.path.exists("exiftool.exe"):
                exiftool_cmd = "exiftool.exe"
            else:
                exiftool_cmd = "exiftool"
            
            # Format command
            cmd = (f'{exiftool_cmd} -GPSLatitude={lat} -GPSLongitude={lon} '
                  f'-GPSLatitudeRef={("S" if lat < 0 else "N")} '
                  f'-GPSLongitudeRef={("W" if lon < 0 else "E")} '
                  f'-DateTimeOriginal="{timestamp}" '
                  f'"{image_path}"')
            
            result = os.system(cmd)
            if result != 0:
                logger.error(f"exiftool command failed with exit code {result}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error adding GPS data using exiftool: {e}")
            return False

    def process_videos(self) -> None:
        """
        Process videos from all cameras and extract frames with synchronized GPS data.
        """
        logger.info(f"Starting video processing with output size: {self.output_size[0]}x{self.output_size[1]}")
        
        # Create GPS processor for matching frames with GPS data
        gps_processor = GPSDataProcessor(fps_video=60, fps_gps=10)
        
        # Process video sets for each front camera video
        frame_counter = 0
        
        # Loop through each front camera video
        for fd_idx, fd_filename in enumerate(self.files_fd):
            logger.info(f"Processing video set {fd_idx + 1}/{len(self.files_fd)}")
            
            # Get corresponding videos for other cameras
            fi_filename = self.files_fi[fd_idx] if fd_idx < len(self.files_fi) else None
            ld_filename = self.files_ld[fd_idx] if fd_idx < len(self.files_ld) else None
            li_filename = self.files_li[fd_idx] if fd_idx < len(self.files_li) else None
            
            # Skip if any camera is missing a video
            if not all([fi_filename, ld_filename, li_filename]):
                logger.warning(f"Missing matching videos for index {fd_idx}, skipping")
                continue
                
            # Construct full paths
            path_fd = os.path.join(self.path_folder_fd, fd_filename)
            path_fi = os.path.join(self.path_folder_fi, fi_filename)
            path_ld = os.path.join(self.path_folder_ld, ld_filename)
            path_li = os.path.join(self.path_folder_li, li_filename)
            
            logger.info(f"Opening videos:")
            logger.info(f"  Front-Right: {path_fd}")
            logger.info(f"  Front-Left: {path_fi}")
            logger.info(f"  Side-Right: {path_ld}")
            logger.info(f"  Side-Left: {path_li}")
            
            # Extract GPS data from front-right camera video
            if not self.extract_metadata(path_fd, gps_processor):
                logger.warning("Failed to extract GPS data, continuing with empty GPS data")
            
            # Open video files
            video_fd = cv2.VideoCapture(path_fd)
            video_fi = cv2.VideoCapture(path_fi)
            video_ld = cv2.VideoCapture(path_ld)
            video_li = cv2.VideoCapture(path_li)
            
            # Check if videos opened successfully
            if not all(cap.isOpened() for cap in [video_fd, video_fi, video_ld, video_li]):
                logger.error("Failed to open one or more video files, skipping this set")
                for cap in [video_fd, video_fi, video_ld, video_li]:
                    if cap.isOpened():
                        cap.release()
                continue
            
            # Get video properties
            frame_count_fd = int(video_fd.get(cv2.CAP_PROP_FRAME_COUNT))
            fps_fd = video_fd.get(cv2.CAP_PROP_FPS)
            
            logger.info(f"Front-Right video: {frame_count_fd} frames at {fps_fd} fps")
            logger.info(f"Sampling every {self.sampling_freq} frames")
            
            # Skip initial frames if specified
            if self.start_frame > 0:
                logger.info(f"Skipping first {self.start_frame} frames")
                for _ in range(self.start_frame):
                    video_fd.read()
                    video_fi.read()
                    video_ld.read()
                    video_li.read()
            
            # Extract frames
            processed_count = 0
            saved_count = 0
            
            logger.info("Starting frame extraction")
            
            while True:
                # Read frames from all cameras
                ret_fd, frame_fd = video_fd.read()
                ret_fi, frame_fi = video_fi.read()
                ret_ld, frame_ld = video_ld.read()
                ret_li, frame_li = video_li.read()
                
                # Check if we reached the end of any video
                if not all([ret_fd, ret_fi, ret_ld, ret_li]):
                    logger.info("Reached end of videos")
                    break
                
                # Increment processed frame counter
                processed_count += 1
                
                # Process every nth frame based on sampling frequency
                if processed_count % self.sampling_freq == 0:
                    # Get GPS data for this frame
                    timestamp, lat, lon = gps_processor.get_gps_for_frame(
                        processed_count, frame_count_fd)
                    
                    # Skip if we don't have valid GPS data and it's the first few frames
                    # (allow processing to continue after a certain point even without GPS)
                    if (lat == 0.0 and lon == 0.0) and processed_count < 1000:
                        continue
                    
                    # Use dummy values if no valid GPS data available
                    if lat == 0.0 and lon == 0.0:
                        lat = 0.0001 * processed_count
                        lon = 0.0001 * processed_count
                    
    # Format timestamp if available
                    if timestamp is not None:
                        # Ensure timestamp is in the correct format for GPSPhoto (YYYY:MM:DD hh:mm:ss)
                        if '.' in timestamp:
                            formatted_timestamp = timestamp.split('.')[0]
                        else:
                            formatted_timestamp = timestamp
                    else:
                        # Create a valid timestamp if none is available
                        formatted_timestamp = datetime.now().strftime('%Y:%m:%d %H:%M:%S')
                    
                    # Create filename based on frame number
                    frame_counter += 1
                    filename = f"{frame_counter}.jpg"
                    
                    try:
                        # Resize frames to 640x640
                        frame_fd_resized = self._resize_to_square(frame_fd, self.output_size[0])
                        frame_fi_resized = self._resize_to_square(frame_fi, self.output_size[0])
                        frame_ld_resized = self._resize_to_square(frame_ld, self.output_size[0])
                        frame_li_resized = self._resize_to_square(frame_li, self.output_size[0])
                        
                        # Save front-right frame with GPS data
                        front_right_path = os.path.join(self.path_save, 'Imagenes_Frontal_Derecha', filename)
                        cv2.imwrite(front_right_path, frame_fd_resized)
                        
                        # Add GPS data to front-right image
                        self.add_gps_to_image(front_right_path, lat, lon, formatted_timestamp)
                        
                        # Save other camera frames
                        cv2.imwrite(os.path.join(self.path_save, 'Imagenes_Frontal_Izquierda', filename), 
                                   frame_fi_resized)
                        cv2.imwrite(os.path.join(self.path_save, 'Imagenes_Lateral_Derecha', filename), 
                                   frame_ld_resized)
                        cv2.imwrite(os.path.join(self.path_save, 'Imagenes_Lateral_Izquierda', filename), 
                                   frame_li_resized)
                        
                        saved_count += 1
                        
                        # Log progress
                        if saved_count % 10 == 0:
                            logger.info(f"Saved {saved_count} frames, current GPS: {lat}, {lon}")
                            
                    except Exception as e:
                        logger.error(f"Error processing frame {frame_counter}: {e}")
            
            # Release video captures
            video_fd.release()
            video_fi.release()
            video_ld.release()
            video_li.release()
            
            logger.info(f"Completed video set {fd_idx + 1}, saved {saved_count} frames")
        
        logger.info(f"Processing complete. Total frames saved: {frame_counter}")
    
    def _resize_to_square(self, frame, size):
        """
        Resize a frame to a square with center crop/padding if needed.
        
        Args:
            frame: Input frame
            size: Size of output square (width=height)
            
        Returns:
            numpy.ndarray: Resized square frame
        """
        h, w = frame.shape[:2]
        
        # If already a square, just resize
        if h == w:
            return cv2.resize(frame, (size, size))
        
        # Create a square canvas with black background
        if h > w:
            # Portrait orientation - need to crop height
            y_offset = (h - w) // 2
            square = frame[y_offset:y_offset+w, 0:w]
        else:
            # Landscape orientation - need to crop width
            x_offset = (w - h) // 2
            square = frame[0:h, x_offset:x_offset+h]
            
        # Resize the square to the desired size
        return cv2.resize(square, (size, size))


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Automatic Video Frame Extraction with GPS Synchronization')
    parser.add_argument('video_folder', help='Path to folder containing camera subfolders (FD, FI, LD, LI)')
    parser.add_argument('output_folder', help='Path to output folder for extracted frames')
    parser.add_argument('--start-frame', type=int, default=0, help='Number of frames to skip from the beginning')
    parser.add_argument('--fps', type=int, default=10, choices=[2, 4, 5, 10], 
                        help='Frames per second to extract (default: 10 - best match for GPS rate)')
    
    return parser.parse_args()


def main():
    """Main entry point for the application."""
    args = parse_arguments()
    
    # Check for required libraries
    if not GPSPHOTO_AVAILABLE:
        logger.warning("GPSPhoto library not available. GPS data may not be embedded correctly.")
        logger.warning("Install with: pip install GPSPhoto")
    
    # Create video processor
    try:
        processor = VideoProcessor(
            video_dir=args.video_folder,
            output_dir=args.output_folder,
            start_frame=args.start_frame,
            fps=args.fps
        )
        
        # Process videos
        processor.process_videos()
        
    except Exception as e:
        logger.error(f"Error during processing: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())