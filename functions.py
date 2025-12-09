'''
This class is responsible for manipulating the image such as Shrinking, Sizing up, etc.
'''

import numpy as np
import cv2
from colormaps import opencv_colormaps


def to_bone_color(picture):
    img_bgr = cv2.cvtColor(picture, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    bone_bgr = cv2.applyColorMap(gray, cv2.COLORMAP_BONE)
    img = cv2.cvtColor(bone_bgr, cv2.COLOR_BGR2RGB)
    return img

def return_color_map(map):

    try:return opencv_colormaps[map]

    except: return

def to_sepia(picture):
    sepia_bgr_kernel = np.array([
                [0.131, 0.534, 0.272],
                [0.168, 0.686, 0.349],
                [0.189, 0.769, 0.393],
    ], dtype=np.float32)
    bgr = cv2.cvtColor(picture, cv2.COLOR_RGB2BGR).astype(np.float32)
    sep = cv2.transform(bgr, sepia_bgr_kernel)
    sep = np.clip(sep, 0, 255).astype(np.uint8)
    img = cv2.cvtColor(sep, cv2.COLOR_BGR2RGB)
    return img

def to_grayscale(picture):
    gray = cv2.cvtColor(picture, cv2.COLOR_RGB2GRAY)
    img = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)

    return img

