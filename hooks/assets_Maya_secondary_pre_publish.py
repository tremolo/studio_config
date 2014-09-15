import os
import maya.cmds as cmds

import tank
from tank import Hook
from tank import TankError

class PrePublishHook(Hook):
	"""
	Single hook that implements pre-publish functionality
	"""
	def execute(self, tasks, work_template, progress_cb, **kwargs):
		"""
		Main hook entry point
		:tasks:         List of tasks to be pre-published.  Each task is be a 
						dictionary containing the following keys:
						{   
							item:   Dictionary
									This is the item returned by the scan hook 
									{   
										name:           String
										description:    String
										type:           String
										other_params:   Dictionary
									}

							output: Dictionary
									This is the output as defined in the configuration - the 
									primary output will always be named 'primary' 
									{
										name:             String
										publish_template: template
										tank_type:        String
									}
						}

		:work_template: template
						This is the template defined in the config that
						represents the current work file

		:progress_cb:   Function
						A progress callback to log progress during pre-publish.  Call:

							progress_cb(percentage, msg)

						to report progress to the UI

		:returns:       A list of any tasks that were found which have problems that
						need to be reported in the UI.  Each item in the list should
						be a dictionary containing the following keys:
						{
							task:   Dictionary
									This is the task that was passed into the hook and
									should not be modified
									{
										item:...
										output:...
									}

							errors: List
									A list of error messages (strings) to report    
						}
		"""       
		results = []

		# validate tasks:
		for task in tasks:
			item = task["item"]
			output = task["output"]
			errors = []

			# report progress:
			progress_cb(0, "Validating", task)

			 # pre-publish model output
			if output["name"] == "prop":
				errors.extend(self._validate_item_for_prop_publish(item))
			elif output["name"] == "set":
				errors.extend(self._validate_item_for_set_publish(item))
			elif output["name"] == "character":
				errors.extend(self._validate_item_for_character_publish(item))
			elif output["name"] == "vehicle":
				errors.extend(self._validate_item_for_vehicle_publish(item))
			elif output["name"] == "poslist":
				errors.extend(self._validate_item_for_positionlist_publish(item))
			else:
				# don't know how to publish this output types!
				errors.append("Don't know how to publish this item!")       

			# if there is anything to report then add to result
			if len(errors) > 0:
				# add result:
				results.append({"task":task, "errors":errors})

			progress_cb(100)

		return results

	def _validate_item_for_prop_publish(self, item):
		"""
		Validate that the item is valid to be exported 
		as an asset
		"""
		
		assetName = item["name"]
		objectName = item["other_params"]["propName"]
		assetType = item["type"]
		
		errors = []
		# check that the group still exists:
		if not cmds.objExists(objectName):
			errors.append("This group couldn't be found in the scene!")
		
		else:
			# Deselect all
			cmds.select(deselect=True)
			# Use selection to get all the children of current objectlocator
			cmds.select(objectName, hierarchy=True, add=True)
			# Get only the selected items. (if necessary take only certain types to export!)
			sel=cmds.ls(selection=True, showType=True)
			
			meshesFound = False
			for s in sel:
				if cmds.ls(s, type="mesh"):
					meshesFound = True
					break
			
			if not meshesFound:
				errors.append("This group doesn't appear to contain any meshes!")
			cmds.select(deselect=True)			
			
		# finally return any errors
		return errors
		
	def _validate_item_for_set_publish(self, item):
		"""
		Validate that the item is valid to be exported 
		as an asset
		"""
		
		assetName = item["name"]
		objectName = item["other_params"]["propName"]
		assetType = item["type"]
		
		errors = []
		# check that the group still exists:
		if not cmds.objExists(objectName):
			errors.append("This group couldn't be found in the scene!")
		
		else:
			# Deselect all
			cmds.select(deselect=True)
			# Use selection to get all the children of current objectlocator
			cmds.select(objectName, hierarchy=True, add=True)
			# Get only the selected items. (if necessary take only certain types to export!)
			sel=cmds.ls(selection=True, showType=True)
			
			meshesFound = False
			for s in sel:
				if cmds.ls(s, type="locator"):
					meshesFound = True
					break
				elif cmds.ls(s, type="mesh"):
					meshesFound = True
					break
			
			if not meshesFound:
				errors.append("This group doesn't appear to contain any locators or meshes!")
			cmds.select(deselect=True)			
			
		# finally return any errors
		return errors	
		
	def _validate_item_for_character_publish(self, item):
		assetName = item["name"]
		objectName = item["other_params"]["propName"]
		assetType = item["type"]
		
		errors = []
		errors.append("This group is not ready for export!")
			
		# finally return any errors
		return errors		
	def _validate_item_for_vehicle_publish(self, item):
		assetName = item["name"]
		objectName = item["other_params"]["propName"]
		assetType = item["type"]
		
		errors = []
		errors.append("This group is not ready for export!")
			
		# finally return any errors
		return errors		
	def _validate_item_for_positionlist_publish(self, item):		
		assetName = item["name"]
		objectName = item["other_params"]["propName"]
		assetType = item["type"]
		
		errors = []
		errors.append("This group is not ready for export!")
			
		# finally return any errors
		return errors