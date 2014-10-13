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
import shutil
import photoshop

import tank
from tank import Hook
from tank import TankError

class PublishHook(Hook):
	"""
	Single hook that implements publish functionality for secondary tasks
	"""    
	def execute(self, tasks, work_template, comment, thumbnail_path, sg_task, primary_task, primary_publish_path, progress_cb, **kwargs):
		"""
		Main hook entry point
		:param tasks:                   List of secondary tasks to be published.  Each task is a 
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
						
		:param work_template:           template
										This is the template defined in the config that
										represents the current work file
			   
		:param comment:                 String
										The comment provided for the publish
						
		:param thumbnail:               Path string
										The default thumbnail provided for the publish
						
		:param sg_task:                 Dictionary (shotgun entity description)
										The shotgun task to use for the publish    
						
		:param primary_publish_path:    Path string
										This is the path of the primary published file as returned
										by the primary publish hook
						
		:param progress_cb:             Function
										A progress callback to log progress during pre-publish.  Call:
										
											progress_cb(percentage, msg)
											 
										to report progress to the UI
						
		:param primary_task:            The primary task that was published by the primary publish hook.  Passed
										in here for reference.  This is a dictionary in the same format as the
										secondary tasks above.
		
		:returns:                       A list of any tasks that had problems that need to be reported 
										in the UI.  Each item in the list should be a dictionary containing 
										the following keys:
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
		
		doc = photoshop.app.activeDocument
		if doc is None:
			raise TankError("There is no currently active document!")
		
		scene_path = doc.fullName.nativePath
		if not work_template.validate(scene_path):
			raise TankError("File '%s' is not a valid work path, unable to publish!" % scene_path)
		
		layers = doc.artLayers
		layerSets = doc.layerSets
		layers = [layers.index(i) for i in xrange(layers.length)]
		original_visibility_layers = [layer.visible for layer in layers]
		layerSets = [layerSets.index(i) for i in xrange(layerSets.length)]
		original_visibility_layerSets = [layerSet.visible for layerSet in layerSets]
		
		layersDict = {}
		
		for layer in layers:
			layer.visible = False
			layersDict[layer.name] = layer
		for layerSet in layerSets:
			layerSet.visible = False
			layersDict[layerSet.name] = layerSet
		
		# publish all tasks:
		for task in tasks:
			item = task["item"]
			itemName = item["name"]
			itemType = item["type"]
			output = task["output"]
			publish_template = output["publish_template"]
			errors = []
			message = ""
			# report progress:
			progress_cb(0, "Publishing", task)
			if itemType == "layer" or itemType == "layerSet":
				for i in layersDict:
					layersDict[i].visible = False
					
				# publish item here, e.g.
				try:
					progress_cb(25, "Processing %s" %itemName)
					if itemName in layersDict:
						currentLayer = layersDict[itemName]
						currentLayer.visible = True
						fields = work_template.get_fields(scene_path)
						fields["channel"] = itemName
						publish_path = publish_template.apply_fields(fields)
						publish_name = os.path.basename(publish_path)
						message += "\nTARGET = %s" %(publish_path)
						
						if publish_path:
							progress_cb(50, "Saving PNG...")
							### TODO : Check if png should be 16 or 8 bit???
							publish_file_path = photoshop.RemoteObject('flash.filesystem::File', publish_path)
							png_options = photoshop.RemoteObject('com.adobe.photoshop::PNGSaveOptions')
							png_options.interlaced = False
							message += "\nOPTIONS : %s" %str(png_options)

							# save as a copy
							doc.saveAs(publish_file_path, png_options, True)     
						message += "\nSAVED.\n"
							
							
						progress_cb(75, "Registering the publish")
						tank_publish = self._register_publish(publish_path, 
							publish_name, 
							sg_task, 
							fields["version"], 
							output["tank_type"],
							comment,
							publish_path, 
							context = self.parent.context,
							dependency_paths=[])
						message += "\nPublished & ENDED"
						# print azerty

				except:
					# don't know how to publish this output types!
					errors.append("Don't know how to publish this item!")   
					errors.append(message)   

			# if there is anything to report then add to result
			if len(errors) > 0:
				# add result:
				results.append({"task":task, "errors":errors})
			 
			progress_cb(100)
			 
		for(i, layer) in enumerate(layers):
			layer.visible = original_visibility_layers[i]
		for(i, layerSet) in enumerate(layerSets):
			layerSet.visible = original_visibility_layerSets[i]
			 
		return results


	def _register_publish(self, path, name, sg_task, publish_version, tank_type, comment, thumbnail_path, context = None, dependency_paths=None):
		"""
		Helper method to register publish using the 
		specified publish info.
		"""
		# construct args:
		args = {
			"tk": self.parent.tank,"context": context,"comment": comment,"path": path,
			"name": name,"version_number": publish_version,"thumbnail_path": thumbnail_path,
			"task": sg_task,"dependency_paths": dependency_paths,"published_file_type":tank_type,
			"user": self.parent.context.user,"created_by": self.parent.context.user
		}

		# register publish;
		sg_data = tank.util.register_publish(**args)
		print 'Register in shotgun done!'
		
		return sg_data
	