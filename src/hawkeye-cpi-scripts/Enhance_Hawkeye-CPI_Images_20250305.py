#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script for processing images, enhancing contrast, and converting white backgrounds to transparency.

Purpose:
    - The script takes images from an input directory, applies image processing techniques to enhance contrast,
      and saves the results in an output directory.

Usage:
    python3 Enhance_Hawkeye-CPI_Images_20250227.py -input_dir /path/to/input -output_dir /path/to/output

Example:
    python3 Enhance_Hawkeye-CPI_Images_20250227.py -input_dir ./raw_images -output_dir ./processed_images

Arguments:
    -input_dir   : (Required) Path to the directory containing input PNG images.
    -output_dir  : (Required) Path to the directory where processed images will be saved.

Help:
    Use the `-h` flag to display this message:
        python3 Enhance_Hawkeye-CPI_Images_20250227.py -h
        
Modifications:
    Christian Nairy <christian.nairy@und.edu> - 2025/02/26:
        Written
"""

from multiprocessing import Pool, cpu_count
import os
import cv2
import numpy as np
import glob
import argparse
import matplotlib.pyplot as plt
from skimage import io, color, filters, exposure
from scipy import ndimage
from PIL import Image  # For saving with 300 DPI
from tqdm import tqdm

global h_particle, w_particle

def debug_thresholding(image, step_name):
    plt.figure(figsize=(5, 5), dpi=300)
    plt.imshow(image, cmap='gray')
    plt.title(step_name)
    plt.axis('off')
    plt.show()

def fill_holes_morphologically(binary_image, kernel_size=1, iterations=1):
    binary_image = (binary_image * 255).astype(np.uint8) if binary_image.dtype != np.uint8 else binary_image
    adaptive_kernel_size = min(kernel_size, max(binary_image.shape) // 100)
    kernel = np.ones((adaptive_kernel_size, adaptive_kernel_size), np.uint8)
    open_image = binary_image.copy()
    for _ in range(iterations):
        open_image = cv2.morphologyEx(open_image, cv2.MORPH_CLOSE, kernel)
    return open_image

def extract_red_mask(original_image, binary_image):
    filled_image = ndimage.binary_fill_holes(binary_image).astype(np.uint8)
    mask = filled_image - binary_image
    mask = (mask * 255).astype(np.uint8)
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=1)
    return mask

def create_radial_gradient(shape):
    h, w = shape
    y, x = np.indices((h, w))
    center_x, center_y = w // 2, h // 2
    radius = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
    radius = radius / np.max(radius)
    return (255 - (radius * 125)).astype(np.uint8)

def enhance_contrast(image):
    return exposure.equalize_adapthist(image, clip_limit=0.017) * 255

def apply_mask_and_radial_background(original_image, mask):
    gradient = create_radial_gradient(original_image.shape)
    enhanced_image = enhance_contrast(original_image)
    particle = np.where(mask == 255, enhanced_image, 255)
    return np.where(mask == 255, particle, gradient)

def pad_to_standard_fov(image, target_size=(1024, 1024)):
    global h_particle, w_particle
    h_particle, w_particle = image.shape[:2]
    pad_y = max((target_size[0] - h_particle) // 2, 0)
    pad_x = max((target_size[1] - w_particle) // 2, 0)
    return cv2.copyMakeBorder(image, pad_y, pad_y, pad_x, pad_x, cv2.BORDER_CONSTANT, value=255)

def add_scale_bar(image, binary_mask, microns_per_pixel=2.3, scale_length_microns=500):
    scale_length_pixels = int(scale_length_microns / microns_per_pixel)
    bar_height = 10
    output_image = cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_GRAY2RGB)
    
    start_y = round((1024 - h_particle) / 2) - 15
    start_x = round((1024 - w_particle) / 2)
    end_x = start_x + scale_length_pixels
    end_y = start_y + bar_height
    
    cv2.rectangle(output_image, (start_x, start_y), (end_x, end_y), (255, 0, 0), -1)
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(output_image, "500 microns", (start_x + 25, start_y - 5), font, 0.8, (255, 0, 0), 2, cv2.LINE_AA)
    return output_image

def process_image(image_path, output_folder):
    global h_particle, w_particle
    image = io.imread(image_path)
    gray_image = color.rgb2gray(image) * 255 if len(image.shape) == 3 else image
    gray_image = gray_image.astype(np.uint8)
    
    h_particle, w_particle = gray_image.shape[:2]

    border_size = 10
    gray_image = cv2.copyMakeBorder(
        gray_image, border_size, border_size, border_size, border_size, 
        cv2.BORDER_CONSTANT, value=190
    )

    thresh = filters.threshold_otsu(gray_image)
    adjusted_thresh = thresh * 1.05
    binary_image = gray_image > adjusted_thresh

    closed_binary_image = fill_holes_morphologically(binary_image, iterations=1)
    mask = extract_red_mask(gray_image, closed_binary_image)

    final_image = apply_mask_and_radial_background(gray_image, mask)
    final_image_no_scale = final_image[border_size:-border_size, border_size:-border_size]

    padded_image = pad_to_standard_fov(final_image_no_scale)
    final_image_with_scale = add_scale_bar(padded_image, closed_binary_image)
    
    os.makedirs(output_folder, exist_ok=True)
    save_path = os.path.join(output_folder, os.path.basename(image_path).replace('.png', '_enhanced.png'))
    plt.imsave(save_path, final_image_with_scale, cmap='gray', dpi=300)

def process_image_wrapper(args):
    """Wrapper function to unpack arguments for process_image."""
    return process_image(*args)

def convert_image_to_transparent(image_path):
    image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if image.shape[-1] != 4:
        image = cv2.cvtColor(image, cv2.COLOR_RGB2RGBA)

    white_mask = (image[:, :, 0] == 255) & (image[:, :, 1] == 255) & (image[:, :, 2] == 255)
    image[:, :, 3] = np.where(white_mask, 0, 255)

    pil_image = Image.fromarray(image)
    pil_image.save(image_path, dpi=(300, 300))

def rename_and_cleanup(file_path):
    new_name = file_path.replace("_transparent.png", "_enhanced.png")
    os.rename(file_path, new_name)

def process_images_in_subdirectories(input_root, output_root):
    all_image_tasks = []
    for root, _, files in os.walk(input_root):
        for file in files:
            if file.lower().endswith('.png'):
                input_path = os.path.join(root, file)
                output_subdir = root.replace(input_root, output_root)
                os.makedirs(output_subdir, exist_ok=True)
                all_image_tasks.append((input_path, output_subdir))
        
        print(f"Processing images in '{root}'...")

    with Pool(processes=28) as pool:
        for _ in tqdm(pool.imap_unordered(process_image_wrapper, all_image_tasks), 
                      total=len(all_image_tasks), 
                      desc="Processing Images"):
            pass

def convert_white_to_transparent(output_root):
    image_files = glob.glob(os.path.join(output_root, "**", "*_enhanced.png"), recursive=True)
    print(f"Converting {len(image_files)} images to transparency...")

    with Pool(processes=28) as pool:
        for _ in tqdm(pool.imap_unordered(convert_image_to_transparent, image_files), 
                      total=len(image_files), 
                      desc="Converting to Transparent"):
            pass

def cleanup_and_rename(output_root):
    files_to_cleanup = glob.glob(os.path.join(output_root, "**", "*_transparent.png"), recursive=True)
    print(f"Cleaning up and renaming {len(files_to_cleanup)} images...")

    with Pool(processes=28) as pool:
        for _ in tqdm(pool.imap_unordered(rename_and_cleanup, files_to_cleanup), 
                      total=len(files_to_cleanup), 
                      desc="Cleaning Up and Renaming"):
            pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhance PNG images from multiple subdirectories.")
    parser.add_argument("-input_dir", type=str, required=True, help="Path to the root input directory.")
    parser.add_argument("-output_dir", type=str, required=True, help="Path to the root output directory.")
    args = parser.parse_args()

    process_images_in_subdirectories(args.input_dir, args.output_dir)
    convert_white_to_transparent(args.output_dir)
    cleanup_and_rename(args.output_dir)

    print("All images processed successfully!")
