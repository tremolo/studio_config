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
import maya.cmds as cmds

import tank
from tank import Hook
from tank import TankError

import sgtk
from sgtk.platform import Application

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
		
		# get the main scene:
		scene_name = cmds.file(query=True, sn=True)
		if not scene_name:
			raise TankError("Please Save your file before Publishing")
		
		scene_path = os.path.abspath(scene_name)
		name = os.path.basename(scene_path)
		# tk = self.parent.tank
		tk = sgtk.sgtk_from_path(scene_path)
		tk.reload_templates()

		scene_template = tk.template_from_path(scene_path)
		flds = scene_template.get_fields(scene_path)
		
		# create the primary item - this will match the primary output 'scene_item_type':            
		items.append({"type": "work_file", "name": name})
		AssetReso = flds.get('Resolution')
		print 50*"*"
		print AssetReso
		print 50*"*"
		if AssetReso is None:
			# items.append({"type": "setting","name": "High resolution","description": "","selected":True})
			items.append({"type": "setting_high","name": "High resolution","description": "","selected":False})
			# items.append({"type": "setting_high","name": "High resolution"})
			items.append({"type": "setting_low","name": "Low resolution","description": "","selected":False})
			# items.append({"type": "setting_low","name": "Low resolution"})
		if AssetReso == 'hi':
			items.append({"type": "setting_high","name": "High resolution","description": "","selected":True})
			items.append({"type": "setting_low","name": "Low resolution","description": "","selected":False})
		if AssetReso == 'lo':
			items.append({"type": "setting_high","name": "High resolution","description": "","selected":False})
			items.append({"type": "setting_low","name": "Low resolution","description": "","selected":True})
		# if there is any geometry in the scene (poly meshes or nurbs patches), then
		# add a geometry item to the list:
		# if cmds.ls(geometry=True, noIntermediate=True):
			# items.append({"type":"geometry", "name":"All Scene Geometry"})

		return items
