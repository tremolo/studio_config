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
				
		items = []
		layersNames = ["DIF", "SPC", "REF"]
		
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
			print layer.name
			if layer.name in layersNames:
				items.append({"type": "layer", "name": layer.name, "description": "Difuse layer", "other_params":{"shortName":layer.name}})
			else:
				print layer.name
				
		for layerSet in layerSets:
			if layerSet.name in layersNames:
				items.append({"type": "layerSet", "name": layerSet.name, "description": "Difuse layer", "other_params":{"shortName":layerSet.name}})
			else:
				print layerSet.name
		
		return items
