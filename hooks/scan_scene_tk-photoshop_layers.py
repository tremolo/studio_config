# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import photoshop

import tank
from tank import Hook
from tank import TankError

class ScanSceneHook(Hook):
	"""
	Hook to scan scene for items to publish
	"""
	
	def execute(self, **kwargs):
		"""
		Main hook entry point
		:returns:       A list of any items that were found to be published.  
						Each item in the list should be a dictionary containing 
						the following keys:
						{
							type:   String
									This should match a scene_item_type defined in
									one of the outputs in the configuration and is 
									used to determine the outputs that should be 
									published for the item
									
							name:   String
									Name to use for the item in the UI
							
							description:    String
											Description of the item to use in the UI
											
							selected:       Bool
											Initial selected state of item in the UI.  
											Items are selected by default.
											
							required:       Bool
											Required state of item in the UI.  If True then
											item will not be deselectable.  Items are not
											required by default.
											
							other_params:   Dictionary
											Optional dictionary that will be passed to the
											pre-publish and publish hooks
						}
		"""   
		
		# with open(r"C:\Users\mclaeys\Desktop\photoshopLog.txt", "w") as log:
			# log.write("self.parent\n")
			# log.write("#"*35)
			
			# tempVar = dir(self.parent)
			# for i in tempVar:
				# log.write(str(i) + "\n")
			# log.write("#"*35)
			# log.write("\n")
				
			# log.write("self.parent.sgtk\n")
			# log.write("#"*35)
			# tempVar = dir(self.parent.sgtk)
			# for i in tempVar:
				# log.write(str(i) + "\n")
		
		
		items = []
		# layersNames = {"dif":"png 8bit", "spc":"png 8bit", "bmp":"png 8bit", "rgh":"png 8bit", "nrm":"exr 16bit", "trs":"png 8bit", "sss":"png 8bit", "dsp":"exr 16bit"}
		layersNames = {"dif":"png", "spc":"png", "bmp":"png", "rgh":"png", "nrm":"exr", "trs":"png", "sss":"png", "dsp":"exr"}
		layersFullNames = {"dif":"diffuse", "spc":"specular", "bmp":"bump", "rgh":"rgh", "nrm":"normals", "trs":"trs", "sss":"sss", "dsp":"displace"}
		
		# get the main scene:
		doc = photoshop.app.activeDocument
		if doc is None:
			raise TankError("There is no currently active document!")
		
		if not doc.saved:
			raise TankError("Please Save your file before Publishing")
		
		scene_path = doc.fullName.nativePath
		name = os.path.basename(scene_path)
		
		# create the primary item - this will match the primary output 'scene_item_type':            
		items.append({"type": "work_file", "name": name})

		layers = doc.artLayers
		layerSets = doc.layerSets
		
		layers = [layers.index(i) for i in xrange(layers.length)]
		layerSets = [layerSets.index(i) for i in xrange(layerSets.length)]
		# original_visibility = [layer.visible for layer in layers]
		for layer in layers:
			layerName = layer.name
			lowName = str(layerName).lower()
			if lowName in layersNames:
				items.append({"type": "%sLayer"%layersNames[lowName], "name": layerName, "description": "%s layer" %layersFullNames[lowName], "other_params":{"targetName":lowName,"file_encoding":layersNames[lowName],"type":"layer","tank_type":"%s image"%layersNames[lowName]}})
			else:
				print "Not exporting Layer: %s" %layerName
				
		for layerSet in layerSets:
			layersetName = layerSet.name
			lowName = str(layersetName).lower()
			if lowName in layersNames:
				items.append({"type": "%sLayer"%layersNames[lowName], "name": layersetName, "description": "%s layer" %layersFullNames[lowName], "other_params":{"targetName":lowName,"file_encoding":layersNames[lowName],"type":"layerSet","tank_type":"%s image"%layersNames[lowName]}})
			else:
				print "Not exporting Set: %s" %layersetName
		
		return items
