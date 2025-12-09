'''
This class is responsible for manipulating the image such as Shrinking, Sizing up, etc.
'''

import numpy as np
import cv2

def to_bone_color(picture):
    img_bgr = cv2.cvtColor(picture, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    bone_bgr = cv2.applyColorMap(gray, cv2.COLORMAP_BONE)
    img = cv2.cvtColor(bone_bgr, cv2.COLOR_BGR2RGB)
    return img

def to_shrink(picture):
    img_bgr = cv2.cvtColor(picture, cv2.COLOR_RGB2BGR)
    # cv2.imwrite('originalsize.png', img_bgr)
    # Shrink by 50% and using INTER_AREA for shrinking
    shrink = cv2.resize(img_bgr, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
     # cv2.imwrite('modifiedsize.png', img)
    img = cv2.cvtColor(shrink, cv2.COLOR_BGR2RGB)

    return img

def to_size_up(picture):
    img_bgr = cv2.cvtColor(picture, cv2.COLOR_RGB2BGR)
    # cv2.imwrite('originalsize.png', img_bgr)
    # Size up by 50% and uses INTER_LINEAR for enlarging
    enlarged = cv2.resize(img_bgr, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_LINEAR)
    # cv2.imwrite('modifiedsize2.png', enlarged)
    img = cv2.cvtColor(enlarged, cv2.COLOR_BGR2RGB)

    return img

def to_custom_resize(picture):
    pass