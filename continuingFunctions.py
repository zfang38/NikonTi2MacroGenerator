import os
import numpy as np
import sys
import pickle
import xml.etree.ElementTree as ET

# Write to text file
def writeToFile(filename, data):
    with open(filename, 'w') as f:
        for line in data:
            f.write(line + '\n')

def moveToAlign(current_macro, alignment_fov):
    sample = os.path.basename(current_macro).split('.')[0]
    dir = os.path.dirname(current_macro)
    alignment_fov = int(alignment_fov)

    with open(os.path.join(dir, sample+'_points_tracking.pkl'), 'rb') as f:
        points_tracking = pickle.load(f)
    
    x = points_tracking[alignment_fov-1][0]
    y = points_tracking[alignment_fov-1][1]
    z = points_tracking[alignment_fov-1][2]
    macro = []
    macro.append('StgMoveXY({}, {}, 0);'.format(x, y))
    macro.append('StgMoveZ({}, 0);'.format(z))
    fns = current_macro.split('.')[0]
    writeToFile(fns+'_move_to_align.mac', macro)

def get_save_path(path):
    if not os.path.exists(path):
        return path
    
    dir_path = os.path.dirname(path)
    base_name = os.path.splitext(os.path.basename(path))[0]
    ext = os.path.splitext(path)[1]
    
    counter = 1
    while True:
        new_path = os.path.join(dir_path, f"{base_name}({counter}){ext}")
        if not os.path.exists(new_path):
            return new_path
        counter += 1

def continueMacro(current_macro, alignment_fov, last_fov):
    sample = os.path.basename(current_macro).split('.')[0]
    dir = os.path.dirname(current_macro)
    with open(current_macro, 'r', encoding='utf-8') as f:
        existing_macros = f.read().splitlines()
    with open(os.path.join(dir, sample+'_points_tracking.pkl'), 'rb') as f:
        points_tracking = pickle.load(f)
    shift = (points_tracking[int(last_fov)-1][0]-points_tracking[int(alignment_fov)-1][0],
             points_tracking[int(last_fov)-1][1]-points_tracking[int(alignment_fov)-1][1],
             points_tracking[int(last_fov)-1][2]-points_tracking[int(alignment_fov)-1][2])
    
    out_path = get_save_path(current_macro)
    writeToFile(out_path, existing_macros)

    macro = []
    macro.append('StgMoveXY({}, {}, 1);'.format(shift[0], shift[1]))
    macro.append('StgMoveZ({}, 1);'.format(shift[2]))
    curr_line = 0
    for line in existing_macros:
        curr_line += 1
        if '_' + last_fov in line and 'ImageSaveAs' in line:
            break
    macro = macro + existing_macros[curr_line+1:]
    writeToFile(current_macro, macro)

