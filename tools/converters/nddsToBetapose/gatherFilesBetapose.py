import glob, os
import shutil
import json
import numpy as np
import random
import cv2
import yaml
from distutils.dir_util import copy_tree

imageWidth = 640
imageHeight = 480

def createJPEGImagesAndLabelsJSONFoldersAndContent(output):
	if os.path.exists(output):
		print('deleting old betaposeFormat')
		shutil.rmtree(output)

	os.makedirs(output)
	os.makedirs(output + '/rgb')
	os.makedirs(output + '/depth')
	os.makedirs(output + '/labelsJSON')

	allSubdirs = [x[0] for x in os.walk('./')]
	counter = 0
	counterJson = 0
	counterCs = 0
	offset = 0
	for dir in allSubdirs:
		print(dir + '  ' + str(offset))
		for file in sorted(os.listdir(dir)):
			if file.endswith("_camera_settings.json"):
				shutil.copy(os.path.join(dir, file), os.path.join(output, 'camera.json'))
				#counterJson += 1
			if file.endswith(".json") and not file.endswith("settings.json"):
				file_name = format(offset+int(file.split('.')[0]), '04') + '.json'
				shutil.copy(os.path.join(dir, file), os.path.join(output + '/labelsJSON', file_name))
				counterJson += 1
			if file.endswith(".png") and not file.endswith("cs.png") and not file.endswith("depth.png") and not file.endswith("is.png"):
				file_name = format(offset+int(file.split('.')[0]), '04') + '.png'
				shutil.copy(os.path.join(dir, file), os.path.join(output + '/rgb', file_name))
				counter += 1
			if file.endswith("depth.png"):
				file_name = format(offset+int(file.split('.')[0]), '04') + '.png'
				shutil.copy(os.path.join(dir, file), os.path.join(output + '/depth', file_name))
				counterCs += 1
		if (len(os.listdir(dir)) > 10):
			offset += int((len(os.listdir(dir)) - 2) / 5)

def cleanUselessFoldersBetapose(output):
	shutil.rmtree(output + '/labelsJSON/')
	os.remove(output + '/camera.json')


def createLabelContentForBetapose(output):
	print('Creating labels')
	allSubdirs = [x[0] for x in os.walk(output + '/labelsJSON')]
	counter = 0
	counterReal = 0
	createdCounter = 0
	f = open(os.path.join(output,'gt.yml'), "w+")
	f_c = open(os.path.join(output,'info.yml'), "w+")
	pics2del = []

	with open(os.path.join(output, 'camera.json')) as json_file:  
		c = json.load(json_file)
		c = c['camera_settings'][0]['intrinsic_settings']
		c_mat = np.array([c['fx'], c['s'], c['cx'], 0, c['fy'], c['cy'], 0, 0, 1])

	for dir in allSubdirs:
		for file in sorted(os.listdir(dir)):
			with open(os.path.join(dir, file)) as json_file:  
				data = json.load(json_file)
				created = False
				counterReal += 1
				if (len(data['objects']) > 0):
					for obj in data['objects']:

						number = int(file.split('.')[0])
						bb_x1 = int(obj['bounding_box']['top_left'][1])
						bb_y1 = int(obj['bounding_box']['top_left'][0])

						bb_x2 = int(obj['bounding_box']['bottom_right'][1])
						bb_y2 = int(obj['bounding_box']['bottom_right'][0])

						if (bb_x1 < 0 or bb_x1 > imageWidth or bb_x2 < 0 or bb_x2 > imageWidth or bb_y1 < 0 or bb_y1 > imageHeight or bb_y2 < 0 or bb_y2 > imageHeight):
							created = False
							print('failed '+ str(number))
							break
						else:
							r1 = obj['pose_transform'][0][:3]
							r2 = obj['pose_transform'][1][:3]
							r3 = obj['pose_transform'][2][:3]
							r = np.array(r1 + r2 + r3).reshape(3, 3).T.reshape(9)
							t = np.array(obj['location']) * 10
							bb_tl = np.array(obj['bounding_box']['top_left'])
							bb_tl = np.array([bb_tl[1], bb_tl[0]])
							bb_br = np.array(obj['bounding_box']['bottom_right'])
							bb_br = np.array([bb_br[1], bb_br[0]])
							res = bb_br - bb_tl
							bb_tl = bb_tl.astype(int)
							res = res.astype(int)
							res = np.append(bb_tl, res, axis=0)

							f.write(str(createdCounter) + ':\n')
							f.write('- cam_R_m2c: ' + np.array2string(r, precision=8, separator=',', suppress_small=True) + '\n')
							f.write('  cam_t_m2c: ' + np.array2string(t, precision=8, separator=',', suppress_small=True) + '\n')
							f.write('  obj_bb: ' + np.array2string(res, separator=',') + '\n')
							f.write('  obj_id: 1\n')

							f_c.write(str(createdCounter) + ':\n')
							f_c.write('  cam_K: ' + np.array2string(c_mat, precision=8, separator=',', suppress_small=True) + '\n')
							f_c.write('  depth_scale: 1.0\n')
							created = True
							createdCounter += 1
							break

					if not created:
						print('deleting: ' + str(number))
						if (os.path.isfile('../betaposeFormat/rgb/' + format(number, '04') + '.png')):
							os.remove('../betaposeFormat/rgb/' + format(number, '04') + '.png')
						if (os.path.isfile('../betaposeFormat/depth/' + format(number, '04') + '.png')):
							os.remove('../betaposeFormat/depth/' + format(number, '04') + '.png')
					counter += 1
				else:
					pics2del = pics2del + [counterReal]
	f.close()
	f_c.close()
	print(pics2del)
	return pics2del

def renumberInFolder(folder):
	allSubdirs = [x[0] for x in os.walk(folder)]
	counter = 0
	for dir in allSubdirs:
		for file in sorted(os.listdir(dir)):
			os.rename(folder + file, folder + format(counter, '04') + '.png')
			counter+=1

def deletePicsWithoutObjects(output, pics2del):
	print(len(pics2del))
	for picNum in pics2del:
		os.remove(output + '/rgb/' + format(picNum, '04') + '.png')
		os.remove(output + '/depth/' + format(picNum, '04') + '.png')



def reformatForBetapose():
	createJPEGImagesAndLabelsJSONFoldersAndContent('../betaposeFormat')
	pics2del = createLabelContentForBetapose('../betaposeFormat')
	deletePicsWithoutObjects('../betaposeFormat', pics2del)
	renumberInFolder('../betaposeFormat/rgb/')
	renumberInFolder('../betaposeFormat/depth/')
	cleanUselessFoldersBetapose('../betaposeFormat')

reformatForBetapose()
