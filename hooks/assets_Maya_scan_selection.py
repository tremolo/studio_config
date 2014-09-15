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

class ScanSceneHook(Hook):
	"""
	Hook to scan selection for items to publish
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
		
		# load the framework:
		wtd_fw = self.load_framework("tk-framework-wtd_v0.x.x")
		# and then import a module from the framework:
		ppl = wtd_fw.import_module("pipeline")
		
		items = []
		
		# get the main scene:
		scene_name = cmds.file(query=True, sn=True)
		if not scene_name:
			raise TankError("Please Save your file before Publishing")
		
		scene_path = os.path.abspath(scene_name)
		name = os.path.basename(scene_path)
		
		# create the primary item - this will match the primary output 'scene_item_type':            
		items.append({"type": "work_file", "name": name})
		
		
		# Deselect all
		# cmds.select(deselect=True)
		
		# look for root level groups that have meshes as children:
		modelDict = {}
		selectedObjects = cmds.ls(selection = True, allPaths= True)
		
		if selectedObjects == []:
			return items
		
		allObjectList = cmds.ls(cmds.listRelatives(cmds.ls(type = "locator", allPaths= True) ,parent = True, type = "transform", path = True))
		
		objectList = []
		for s in selectedObjects:
			if s in allObjectList:
				objectList.append(s)
			else:
				selectionObjectList = cmds.ls(cmds.listRelatives(cmds.ls(selection = True) ,parent = True, type = "transform", path = True))
				for t in selectionObjectList:
					if t in allObjectList and t not in objectList:
						objectList.append(t)
		
		childrenAndParentsDict, typeDict = getAllParentsAndTypeDict(objectList)
		
		for obj in objectList:
			print '   # Checking object : %s' %obj
			assetName = obj
			tempAssetName = ""
			if "_" in obj:
				if obj.find("_") == obj.rfind("_"):
					tempAssetName = obj.strip("0123456789")
					if tempAssetName.endswith("_"):
						assetName = tempAssetName[ : -1]
					else:
						assetName = assetName[assetName.find("_") +1 : ]
				else:
					assetName = obj[obj.find("_")+1 : ].strip("0123456789")[ : -1]
			
			if assetName in modelDict:
				modelDict[assetName]["other_params"]["amount"] += 1
				modelDict[assetName]["description"] = "objectName : %s, amount in scene : %s" %(obj,modelDict[assetName]["other_params"]["amount"])
				# print 'DOUBLES : ', assetName, obj
				continue
				
			# print 'SINGLES : ', assetName, obj
			# selected = checkReference(obj)		
			
			tempType = None
			if obj.startswith("PRP_"):
				tempType = "Prop"
			elif obj.startswith("SET_") or obj.startswith("SUB_") :
				tempType = "Set"
				selected = False
			elif obj.startswith("CHR_"):
				tempType = "Character"
			elif obj.startswith("VEH_"):
				tempType = "Vehicle"
			elif obj in typeDict:
				tempType = typeDict[obj]
				
			selected = not checkIfAssetExists(self.parent.shotgun, assetName, tempType)
			
			# Use selection to get all the children of "Alembic" objectset
			tempChildren = cmds.listRelatives(obj, allDescendents = False, children = True, path = True)
			cmds.select(tempChildren, hierarchy=True, add=True)
			# Get only the selected items. (if necessary take only certain types to export!)
			sel=cmds.ls(selection=True, showType=True)
			descr = 'objectName : %s' %obj
			modelDict[assetName] = {"type":tempType, "name":assetName, "selected":selected, "description":descr, "other_params":{"selectionDict":sel,"amount":1, "propName":obj}}
			cmds.select(deselect=True)		
			
		for m in modelDict:
			items.append(modelDict[m])
			
		# if len(objectList) > 0:
			# items.append({"type":"poslist", "name":"Positionlist %s" %name, "selected":True, "description":"%s objects in scene" %(len(objectList))})
		
		# print "### testing importstuff ###"
		# testList = ppl.Positionlist()
		# print testList.getList()
		# print "### testing importstuff ###"
		
		cmds.select(selectedObjects, add = False)
		
		return items

		
def getAllParentsAndTypeDict(objectList = None):
	childrenAndParentsDict = {}
	
	if objectList == None:
		objectList = cmds.listRelatives(cmds.ls(type = "locator", allPaths= True) ,parent = True, type = "transform")
	typeDict = {}
	parentsDict = {}
	for obj in objectList:
		if obj not in typeDict:
			typeDict[str(obj)] = "Prop"
		tempParent = cmds.listRelatives(obj, parent = True)
		if tempParent != None:
			typeDict[str(tempParent[0])] = "Set"
			parentsDict[str(obj)] = str(tempParent[0])
		
	for obj in objectList:
		parentList = []
		newChild = obj
		while str(newChild) in parentsDict:
			parent = parentsDict[str(newChild)]
			parentList.append(parent)
			newChild = parent
		childrenAndParentsDict[str(obj)] = parentList
	return childrenAndParentsDict, typeDict
	
def checkReference(obj):
	# tempCheck = cmds.ls(references = True)
	tempCheck = cmds.ls(rn = True)
	# print "REFERENCES : %s" %tempCheck
	if obj in tempCheck:
		return True
	return False
	
def checkIfAssetExists(sg, asset, type = None):
	filters = [ ['code', 'is', asset] ]
	if type != None:
		filters.append(['sg_asset_type', 'is', type])
	
	foundAsset = sg.find_one('Asset', filters)
	
	if foundAsset == None:
		return False
	return True
