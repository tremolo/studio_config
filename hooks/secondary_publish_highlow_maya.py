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
import copy
import shutil
import maya.cmds as cmds
import maya.mel as mel

import tank
from tank import Hook
from tank import TankError

import sgtk
from sgtk.platform import Application

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
		
		tk = self.parent.tank
		scenePath = cmds.file(q=True,sceneName=True)
		scene_template = tk.template_from_path(scenePath)
		flds = scene_template.get_fields(scenePath)
		maya_asset_publish_template = tk.templates["maya_asset_publish"]
		maya_asset_work_template = tk.templates["maya_asset_work"]
		
		
		AssetReso = flds.get('Resolution')
		
		# publish all tasks:
		for task in tasks:
			item = task["item"]
			output = task["output"]
			errors = []
		
			# report progress:
			progress_cb(0, "Publishing", task)

			set_highres = False
			set_lowres = False
			
			
			if item["type"] == "setting_high":
				if item["name"]=="High resolution":
					set_highres = True
			if item["type"] == "setting_low":
				if item["name"]=="Low resolution":
					set_lowres = True
					
			if set_highres:
				flds['Resolution'] = "hi"
			
			if set_lowres:
				flds['Resolution'] = "lo"
				
			publishpath = maya_asset_publish_template.apply_fields(flds)
			fldsIncr = copy.deepcopy(flds)
			fldsIncr['version'] += 1
			workpath = maya_asset_work_template.apply_fields(fldsIncr)
			print publishpath
			cmds.file(rename = publishpath)
			cmds.file(save=True)
			cmds.file(rename = workpath)
			cmds.file(save=True)
			file_to_publish = publishpath
			ctx = tk.context_from_path(file_to_publish)
			user = self.parent.context.user
			
			sgtk.util.register_publish(tk, ctx, file_to_publish, os.path.basename(file_to_publish) , flds['version'], tank_type= "Maya Scene", created_by= user, user=user,updated_by= user )
			print "REGISTER OKAY"
			# if there is anything to report then add to result
			if len(errors) > 0:
				# add result:
				results.append({"task":task, "errors":errors})
			
			progress_cb(100)
			
		return results

'''
		def _register_publish(self, path, name, sg_task, publish_version, tank_type, comment, thumbnail_path, context = None, dependency_paths=None):
			"""
			Helper method to register publish using the 
			specified publish info.
			"""
			# construct args:
			args = {"tk": self.parent.tank,"context": context,"comment": comment,"path": path,"name": name,"version_number": publish_version,"thumbnail_path": thumbnail_path,"task": sg_task,"dependency_paths": dependency_paths,"published_file_type":tank_type,"user": self.parent.context.user,"created_by": self.parent.context.user}

			# print args
			# register publish;
			sg_data = tank.util.register_publish(**args)
			print 'Register in shotgun done!'
			
			return sg_data
'''
