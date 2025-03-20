#!/usr/bin/env python3
"""
Directory Structure Checker
--------------------------
This utility script helps verify the expected directory structure for video processing
"""

import os
import sys
import argparse

def print_directory_structure(base_path, max_depth=3, current_depth=0, prefix=""):
    """Print the directory structure up to a certain depth."""
    if not os.path.exists(base_path):
        print(f"ERROR: Path does not exist: {base_path}")
        return
    
    if current_depth > max_depth:
        print(f"{prefix}...")
        return
    
    if os.path.isdir(base_path):
        print(f"{prefix}📁 {os.path.basename(base_path)}/")
        items = sorted(os.listdir(base_path))
        
        for i, item in enumerate(items):
            item_path = os.path.join(base_path, item)
            if i == len(items) - 1:
                new_prefix = prefix + "    "
                branch = "└── "
            else:
                new_prefix = prefix + "│   "
                branch = "├── "
            
            if os.path.isdir(item_path):
                print_directory_structure(item_path, max_depth, current_depth + 1, prefix + branch)
            else:
                file_size = os.path.getsize(item_path) / (1024 * 1024)  # Size in MB
                print(f"{prefix}{branch}📄 {item} ({file_size:.2f} MB)")
    else:
        print(f"{prefix}📄 {os.path.basename(base_path)}")

def check_camera_folders(video_path):
    """Check if the required camera folders exist."""
    camera_folders = ['FD', 'FI', 'LD', 'LI']
    missing = []
    
    print("\nChecking for required camera folders:")
    for folder in camera_folders:
        folder_path = os.path.join(video_path, folder)
        if os.path.isdir(folder_path):
            video_count = len([f for f in os.listdir(folder_path) 
                             if os.path.isfile(os.path.join(folder_path, f)) 
                             and f.lower().endswith(('.mp4', '.avi', '.mov'))])
            print(f"  ✅ {folder} - Found with {video_count} video files")
        else:
            missing.append(folder)
            print(f"  ❌ {folder} - Not found")
    
    if missing:
        print(f"\nWARNING: Missing camera folders: {', '.join(missing)}")
        print("The script expects videos organized in FD, FI, LD, and LI folders")
    else:
        print("\nAll required camera folders found.")

def main():
    parser = argparse.ArgumentParser(description='Check directory structure for video processing')
    parser.add_argument('--base-path', default=os.getcwd(),
                       help='Base directory to check (default: current directory)')
    args = parser.parse_args()
    
    base_path = args.base_path
    
    print(f"Current working directory: {os.getcwd()}")
    print(f"\nChecking directory structure from: {base_path}")
    print("-" * 50)
    
    # Check for the expected structure
    data_path = os.path.join(base_path, "data")
    videos_path = os.path.join(data_path, "Videos")
    fotos_path = os.path.join(data_path, "Fotos")
    
    if os.path.isdir(data_path):
        print(f"✅ Data directory found: {data_path}")
    else:
        print(f"❌ Data directory NOT found: {data_path}")
    
    if os.path.isdir(videos_path):
        print(f"✅ Videos directory found: {videos_path}")
        
        # List available video folders
        video_folders = [f for f in os.listdir(videos_path) if os.path.isdir(os.path.join(videos_path, f))]
        if video_folders:
            print(f"   Available video folders: {', '.join(video_folders)}")
            
            # Check the most recent video folder for camera subfolders
            most_recent = sorted(video_folders)[-1]
            print(f"\nExamining most recent video folder: {most_recent}")
            check_camera_folders(os.path.join(videos_path, most_recent))
        else:
            print("   No video folders found")
    else:
        print(f"❌ Videos directory NOT found: {videos_path}")
    
    if os.path.isdir(fotos_path):
        print(f"✅ Fotos directory found: {fotos_path}")
    else:
        print(f"❌ Fotos directory NOT found: {fotos_path}")
    
    # Print full directory structure for reference
    print("\nPrinting directory structure:")
    print("-" * 50)
    print_directory_structure(base_path, max_depth=3)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())