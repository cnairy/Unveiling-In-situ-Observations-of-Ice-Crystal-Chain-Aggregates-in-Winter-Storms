#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
#
# Name:
#   Level1_HawkeyeCPI_individual_image_dump.py
#
# Purpose:
#   Read in raw binary Hawkeye-CPI (*roi) files and export individual CPI 
#   particle images that can then be read into KIT MATLAB classification
#   software.
#
# Syntax:
#   ./Level1_HawkeyeCPI_individual_image_dump.py
#
#   Input Hawkeye-CPI binary roi formatted Files:
#       (Ex: 20230115191319.roi)
#
#   Output Files:
#       IMPACTS_HawkeyeCPI_20230115191319191424206_######.png   
#           (Where ###### is the image number)
#
#   Execution Example:
#       Need to be in the directory where your roi files are located. Then:
#       ./Level1_HawkeyeCPI_individual_image_dump.py
#
# Modification History:
#   2023/09/25 - Christian Nairy <christian.nairy@und.edu>
#     Written.
#   2025/03/06 - Christian Nairy <christian.nairy@und.edu>
#     Added muliprocessing capabilities.
#   2025/03/19 - Christian Nairy <christian.nairy@und.edu>
#     Fixed '&' 'and' issue that unnessesarily removed good particles.
#
# Copyright 2025 David Delene
#
# This program is distributed under the terms of the GNU General Public License
#
# This file is part of Airborne Data Processing and Analysis (ADPAA).
#
# ADPAA is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ADPAA is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ADPAA.  If not, see <http://www.gnu.org/licenses/>.
"""

#Imports
import struct
import numpy as np
import os
from PIL import Image
from multiprocessing import Pool

# Define block types
IMAGE_BLOCK = 0xB2E6
METADATA_BLOCK = 0xA3D5

# Main script
input_directory = os.getcwd()
output_base_directory = os.getcwd()
# Create the output base directory if it doesn't exist
os.makedirs(output_base_directory, exist_ok=True)



# Define the processing function for each .roi file
def process_roi_file(filename):
    if not filename.endswith(".roi"):
        return
    
    file_base = os.path.splitext(os.path.basename(filename))[0]
    output_directory1 = os.path.join(output_base_directory, file_base + '_C1')
    output_directory2 = os.path.join(output_base_directory, file_base + '_C2')
    os.makedirs(output_directory1, exist_ok=True)
    os.makedirs(output_directory2, exist_ok=True)

    count = 0
    with open(os.path.join(input_directory, filename), 'rb') as file:
        while True:
            header_format = "<H"
            header_size = struct.calcsize(header_format)
            header_data = file.read(header_size)
            
            if len(header_data) != header_size:
                break
                
            block_type = struct.unpack(header_format, header_data)[0]


 #if Hexdecimal block type equals defined above then format the block information
            if block_type == METADATA_BLOCK:
                # Handle metadata block
                # L = Long, H = int, f = float, B = byte
                meta_format = "<L H H L B B B B H H H H H H H H L B B H f f L B B H H H L L B B L H"
                meta_size = struct.calcsize(meta_format)
                meta_data = file.read(meta_size)
                if len(meta_data) != meta_size:
                    break  # Handle incomplete header
            
                meta_values = struct.unpack(meta_format, meta_data)
                blksize2, ver2, numrois, tot, day, hour, minu, sec, msec, typ, starx, stary, endx, endy, bgrate, bgpdsthresh, nframes, ithresh, roierr, roimin, roiaspe, roifill, roifcount, imgmean, bkgmean, spare, roixpad, roiypad, strobecnt, framessav, imgminval, imgmaxval, nroisaved, checksum = meta_values
                hour = "{:02d}".format(hour)
                minu = "{:02d}".format(minu)
                sec = "{:02d}".format(sec)
                msec = "{:03d}".format(msec)
                time = str(hour + minu + sec + msec)
                

            if block_type == IMAGE_BLOCK:
                image_header_format = "<L H H H H H H H f L L f L L H f f"
                image_header_size = struct.calcsize(image_header_format)
                image_header_data = file.read(image_header_size)
                if len(image_header_data) != image_header_size:
                    break  # Handle incomplete header
            
                image_header_values = struct.unpack(image_header_format, image_header_data)
                blksize, version, sx, sy, ex, ey, pix, flags, leng, starlen, endlen, width, starwid, endwid, roidepth, area, perim = image_header_values
                
                # Check for valid dimensions
                # leng = leng
                totx = ex - sx + 1
                toty = ey - sy + 1
                if totx <= 0 or toty <= 0:
                    print(time)
                    print("Invalid dimensions, skipping block.")
                    continue
                
                if totx > 5000 or version > 5000:
                    print(time)
                    print("Invalid dimensions, skipping block.")
                    continue
                
                roi = np.zeros((toty, totx), dtype=np.uint8)
                
                cur_ptr = file.tell()
                
                # Get the file size
                file_size = os.fstat(file.fileno()).st_size
                
                # Check if there are enough bytes remaining in the file for 'roi'
                if (file_size - cur_ptr) >= roi.size:
                    # Read the 'roi' data from the file
                    roi_data = file.read(roi.size)
                    roi = np.frombuffer(roi_data, dtype=np.uint8).reshape((toty, totx))
                else:
                    # Otherwise, move the file pointer to the end of the file
                    file.seek(0, os.SEEK_END)
                
                array = np.array(roi)
                img = Image.fromarray(array)
                
                # Increment the count for unique image filenames
                # Helps solve the issue where sampling transitions
                # from 23:59:59 - 00:00:00 UTC the next day.
                if int(time) > 1000:
                    date = str(file_base)
                    # print(date)
                    count += 1
                    # Obtain image time
                    time = str(hour + minu + sec + msec)
                    # Obtain image numbers
                    img_num = "{:06d}".format(count)
                    
                    #### PARTICLE THRESHOLD (75 pixels) ESTIMATE ####
                    # 2.3 microns * 75 pixels = 172.5 microns
                    # Eliminates small particles:
                    if int(totx) > 75 and int(toty) > 75:

                        print(f'From file: {filename} - Writing: IMPACTS_HawkeyeCPI_{date}{time}_{img_num}.png')
                        # Save individual images
                        img.save(os.path.join(output_directory1, f'IMPACTS_HawkeyeCPI_{date}{time}_{img_num}_C1.png'))
                        img.save(os.path.join(output_directory2, f'IMPACTS_HawkeyeCPI_{date}{time}_{img_num}_C2.png'))



# Use multiprocessing to process files in parallel
if __name__ == '__main__':
    roi_files = [f for f in os.listdir(input_directory) if f.endswith('.roi')]
    
    # Use 28 CPU cores
    with Pool(28) as pool:
        pool.map(process_roi_file, roi_files)
