import os
import numpy as np
import sys
import pickle
import xml.etree.ElementTree as ET

def writeToFile(filename, data):
    with open(filename, 'w') as f:
        for line in data:
            f.write(line + '\n')

def multipointMacroFromFile(file_dir, fov_scale, n_z, image_dir, macro_dir, focus_channel):
    
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

    if fov_scale == '40x':
        coarse_step = 1.8
        fine_step = 0.6
        z_step = 0.3
    elif fov_scale == '60x':
        coarse_step=1.8
        fine_step=0.6
        z_step = 0.3
    elif fov_scale == '20x':
        coarse_step=5.4
        fine_step = 1.8
        z_step = 0.9
    elif fov_scale == '10x':
        coarse_step = 5.4
        fine_step=1.8
        z_step = 0.9
    else:
        fov_scale = None
    if fov_scale is None:
        print('Invalid objective lens')

    sample = os.path.basename(file_dir).split('.')[0]

    i = 0
    macro = []
    check_macro = []
    macro.append('StgMoveXY({}, {}, 0);'.format(xx[0], yy[0]))
    macro.append('StgMoveZ({}, 0);'.format(zz[0]))
    macro.append('SelectOptConf("{}");'.format(focus_channel))
    macro.append('StgFocusSetCriterion(2);')
    macro.append('StgFocusInRangeTwoPasses(75.00000, {}, {});'.format(coarse_step, fine_step))
    macro.append('ND_SetZSeriesExp(2, 0,0.00000, 0, {}, {}, 0, 1, "", "", "");'.format(z_step, n_z))
    macro.append('ND_RunExperiment(1);')
    macro.append('ImageSaveAs("{}",14,0);'.format(os.path.join(image_dir,sample,sample+'_'+str(i+1).zfill(3)+'.nd2')))
    macro.append('CloseCurrentDocument(0);')

    check_macro.append('StgMoveXY({}, {}, 0);'.format(xx[0], yy[0]))
    check_macro.append('StgMoveZ({}, 0);'.format(zz[0]))
    check_macro.append('SelectOptConf("DAPI");')
    check_macro.append('Wait(0.2);')
    
    curr_x = xx[0]
    curr_y = yy[0]
    curr_z = zz[0]
    imaged_points = [[curr_x, curr_y, curr_z]]
    for i in range(1, len(xx)):
        macro.append('StgMoveXY({}, {}, 1);'.format(xx[i]-xx[i-1], yy[i]-yy[i-1]))
        macro.append('StgMoveZ({}, 0);'.format(zz[i]))
        macro.append('SelectOptConf("{}");'.format(focus_channel))
        macro.append('StgFocusSetCriterion(2);')
        macro.append('StgFocusInRangeTwoPasses(75.00000, {}, {});'.format(coarse_step, fine_step))
        macro.append('ND_SetZSeriesExp(2, 0,0.00000, 0, {}, {}, 0, 1, "", "", "");'.format(z_step, n_z))
        macro.append('ND_RunExperiment(1);')
        macro.append('ImageSaveAs("{}",14,0);'.format(os.path.join(image_dir,sample,sample+'_'+str(i+1).zfill(3)+'.nd2')))
        macro.append('CloseCurrentDocument(0);')
        
        # if i+1 % fov_per_escape == 0:
        #     print(i)
        #     macro.append('StgMoveZ({}, 0);'.format(800))

        check_macro.append('StgMoveXY({}, {}, 1);'.format(xx[i]-xx[i-1], yy[i]-yy[i-1]))
        check_macro.append('StgMoveZ({}, 0);'.format(zz[i]))
        check_macro.append('SelectOptConf("DAPI");')
        check_macro.append('Wait(0.2);')

        curr_x = curr_x + (xx[i]-xx[i-1])
        curr_y = curr_y + (yy[i]-yy[i-1])
        curr_z = zz[i]
        imaged_points.append([curr_x, curr_y, curr_z])

    macro.append('StgMoveZ({},0);'.format(800))
    writeToFile(os.path.join(macro_dir, sample+'.mac'), macro)
    with open(os.path.join(macro_dir, sample+'_points_tracking.pkl'), 'wb') as f:
        pickle.dump(imaged_points, f)
    # pickle.dump({'positions':(x, y, z),'row':row, 'col':col}, open(sample+'_scan_meta.pkl', 'wb'))

    writeToFile(os.path.join(macro_dir, sample+'_check.mac'), check_macro)
    os.makedirs(os.path.join(image_dir, sample), exist_ok=True)
    os.makedirs(macro_dir, exist_ok=True)
    return sample
