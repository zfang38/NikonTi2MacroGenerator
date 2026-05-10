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

def grid(x_min, x_max, y_min, y_max, fov_scale, overlap=0.15):
    x_n = np.ceil((x_max - x_min) / (fov_scale * (1-overlap)))
    y_n = np.ceil((y_max - y_min) / (fov_scale * (1-overlap)))
    x = np.arange(x_min, x_min+(x_n*fov_scale*(1-overlap))+15, fov_scale*(1-overlap))
    y = np.arange(y_min, y_min+(y_n*fov_scale*(1-overlap))+15, fov_scale*(1-overlap))
    xx, yy = np.meshgrid(x, y)
    row, col = xx.shape
    x = xx.flatten()
    y = yy.flatten()
    return x, y,row, col

def focusSurface(top, left, bottom, right):
    x = np.array([top[0], left[0], bottom[0], right[0]])
    y = np.array([top[1], left[1], bottom[1], right[1]])
    z = np.array([top[2], left[2], bottom[2], right[2]])
    A = np.vstack([x, y, np.ones(len(x))]).T
    a, b, c = np.linalg.lstsq(A, z, rcond=None)[0]
    return a, b, c

def generateScanMacroFromFile(file_dir, samples_to_image, fov_scale, n_z, image_dir, macro_dir, focus_channel):

    tree = ET.parse(file_dir)
    root = tree.getroot()
    xx = []
    yy = []
    zz = []
    for item in root.findall('.//dXPosition'):
        xx.append(float(item.attrib['value']))
    for item in root.findall('.//dYPosition'):
        yy.append(float(item.attrib['value']))
    for item in root.findall('.//dZPosition'):
        zz.append(float(item.attrib['value']))
    samples_to_image = samples_to_image.split(',')
    # n_samples = len(samples_to_image)
    sample_positions = []
    for s in samples_to_image:
        i = int(s) - 1
        temp = {}
        temp['top'] = [xx[i*4], yy[i*4], zz[i*4]]
        temp['left'] = [xx[i*4+1], yy[i*4+1], zz[i*4+1]]
        temp['bottom'] = [xx[i*4+2], yy[i*4+2], zz[i*4+2]]
        temp['right'] = [xx[i*4+3], yy[i*4+3], zz[i*4+3]]
        sample_positions.append(temp)

    if fov_scale == '40x':
        fov_scale = 373.6
        coarse_step = 1.8
        fine_step = 0.6
        z_step = 0.3
    elif fov_scale == '60x':
        fov_scale = 249.6
        coarse_step=1.8
        fine_step=0.6
        z_step = 0.3
    elif fov_scale == '20x':
        coarse_step=5.4
        fine_step = 1.8
        fov_scale = 747.26
        z_step = 0.9
    elif fov_scale == '10x':
        coarse_step = 5.4
        fine_step=1.8
        fov_scale = 1497.6
        z_step = 0.9
    else:
        fov_scale = None
    if fov_scale is None:
        print('Invalid objective lens')
    
    sample = os.path.basename(file_dir).split('.')[0]
    samples_id = []
    for j,item in enumerate(sample_positions):
        top_x, top_y, top_z = item['top']
        left_x, left_y, left_z = item['left']
        bottom_x, bottom_y, bottom_z = item['bottom']
        right_x, right_y, right_z = item['right']
    
        max_x = max(top_x, bottom_x, left_x, right_x)
        min_x = min(top_x, bottom_x, left_x, right_x)
        max_y = max(top_y, bottom_y, left_y, right_y)
        min_y = min(top_y, bottom_y, left_y, right_y)
        x, y, row, col = grid(min_x, max_x, min_y, max_y, fov_scale)
        a, b, c = focusSurface((top_x, top_y, top_z),
                            (left_x, left_y, left_z),
                            (bottom_x, bottom_y, bottom_z),
                            (right_x, right_y, right_z))
        z = a*x + b*y + c

        # with open(os.path.join(macro_dir, 'calculated_points.pkl'), 'wb') as f:
        #     pickle.dump([x, y, z], f)
        
        i = 0
        macro = []
        check_macro = []
        macro.append('StgMoveXY({}, {}, 0);'.format(x[0], y[0]))
        macro.append('StgMoveZ({}, 0);'.format(z[0]))
        macro.append('SelectOptConf("{}");'.format(focus_channel))
        macro.append('StgFocusSetCriterion(2);')
        macro.append('StgFocusInRangeTwoPasses(75.00000, {}, {});'.format(coarse_step, fine_step))
        macro.append('ND_SetZSeriesExp(2, 0,0.00000, 0, {}, {}, 0, 1, "", "", "");'.format(z_step, n_z))
        macro.append('ND_RunExperiment(1);')
        macro.append('ImageSaveAs("{}",14,0);'.format(os.path.join(image_dir,sample+'_'+str(samples_to_image[j]).zfill(3),'tile_'+str(i+1).zfill(3)+'.nd2')))
        macro.append('CloseCurrentDocument(0);')
        curr_x = x[0]
        curr_y = y[0]
        curr_z = z[0]
        
        imaged_points = [[curr_x, curr_y, curr_z]]
        for i in range(1, len(x)):
            macro.append('StgMoveXY({}, {}, 1);'.format(x[i]-x[i-1], y[i]-y[i-1]))
            macro.append('StgMoveZ({}, 0);'.format(z[i]))
            # macro.append('SelectOptConf("DAPI");')
            # macro.append('StgFocusSetCriterion(2);')
            # macro.append('StgFocusInRangeTwoPasses(75.00000, {}, {});'.format(coarse_step, fine_step))
            macro.append('ND_SetZSeriesExp(2, 0,0.00000, 0, {}, {}, 0, 1, "", "", "");'.format(z_step, n_z))
            macro.append('ND_RunExperiment(1);')
            macro.append('ImageSaveAs("{}",14,0);'.format(os.path.join(image_dir,sample+'_'+str(samples_to_image[j]).zfill(3),'tile_'+str(i+1).zfill(3)+'.nd2')))
            macro.append('CloseCurrentDocument(0);')
            curr_x = curr_x + x[i]-x[i-1]
            curr_y = curr_y + y[i]-y[i-1]
            curr_z = curr_z + z[i]-z[i-1]

            imaged_points.append([curr_x, curr_y, curr_z])

        macro.append('StgMoveZ({},0);'.format(800))
        writeToFile(os.path.join(macro_dir, sample+'_'+str(samples_to_image[j]).zfill(3)+'.mac'), macro)
        # pickle.dump({'positions':(x, y, z),'row':row, 'col':col}, open(sample+'_scan_meta.pkl', 'wb'))
        with open(os.path.join(macro_dir, sample+'_'+str(samples_to_image[j]).zfill(3)+'_points_tracking.pkl'), 'wb') as f:
            pickle.dump(imaged_points, f)
        
        check_macro = []
        for item in macro:
            if 'StgMoveXY' in item:
                check_macro.append(item)
            elif 'StgMoveZ' in item:
                check_macro.append(item)
                check_macro.append('Wait(0.2);')
        writeToFile(os.path.join(macro_dir, sample+'_'+str(samples_to_image[j]).zfill(3)+'_check.mac'), check_macro)
        os.makedirs(os.path.join(image_dir, sample+'_'+str(samples_to_image[j]).zfill(3)), exist_ok=True)
        os.makedirs(macro_dir, exist_ok=True)
        samples_id.append(sample+'_'+str(samples_to_image[j]).zfill(3))
    return samples_id

def chainingMacro(sample1, sample2, macro_dir):
    with open(os.path.join(macro_dir, sample1+'.mac'), 'r', encoding='utf-8') as f:
        macros1 = f.read().splitlines()
    with open(os.path.join(macro_dir, sample2+'.mac'), 'r', encoding='utf-8') as f:
        macros2 = f.read().splitlines()
    
    with open(os.path.join(macro_dir, sample1+'_points_tracking.pkl'), 'rb') as f:
        points1 = pickle.load(f)
    with open(os.path.join(macro_dir, sample2+'_points_tracking.pkl'), 'rb') as f:
        points2 = pickle.load(f)
    
    diff = (points2[0][0]-points1[-1][0],
            points2[0][1]-points1[-1][1])
    macros1.append("RunMacro(\"{}\");".format(os.path.join(macro_dir, sample2+'.mac')))
    macros2_new = ['StgMoveXY({}, {}, 1);'.format(diff[0], diff[1])]
    macros2_new = macros2_new + macros2[1:]
    writeToFile(os.path.join(macro_dir, sample1+'.mac'), macros1)
    writeToFile(os.path.join(macro_dir, sample2+'.mac'), macros2_new)

    check_macro = []
    check_macro = []
    for item in macros2_new:
        if 'StgMoveXY' in item:
            check_macro.append(item)
        elif 'StgMoveZ' in item:
            check_macro.append(item)
            check_macro.append('Wait(0.2);')
    writeToFile(os.path.join(macro_dir, sample2.split('.')[0]+'_check.mac'), check_macro)
