import os
import shutil
import maya.cmds as cmds
import maya.mel as mel

import tank
from tank import Hook
from tank import TankError

class PublishHook(Hook):
	"""
	Single hook that implements publish functionality for secondary tasks
	"""    
	def execute(self, tasks, work_template, comment, thumbnail_path, sg_task, primary_publish_path, progress_cb, **kwargs):
		"""
		Main hook entry point
		:tasks:         List of secondary tasks to be published.  Each task is a 
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

		:comment:       String
						The comment provided for the publish

		:thumbnail:     Path string
						The default thumbnail provided for the publish

		:sg_task:       Dictionary (shotgun entity description)
						The shotgun task to use for the publish    

		:primary_publish_path: Path string
						This is the path of the primary published file as returned
						by the primary publish hook

		:progress_cb:   Function
						A progress callback to log progress during pre-publish.  Call:

							progress_cb(percentage, msg)

						to report progress to the UI

		:returns:       A list of any tasks that had problems that need to be reported 
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

		# publish all tasks:
		for task in tasks:
			item = task["item"]
			output = task["output"]
			errors = []

			# report progress:
			progress_cb(0, "Publishing", task)
			
			# publish alembic_cache output
			if output["name"] == "prop":
				try:
					print item["name"]
					self._publish_prop_for_item(item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb)
				except Exception, e:
					errors.append("Publish failed - %s" % e)
			else:
				# don't know how to publish this output types!
				errors.append("Don't know how to publish this item!")

			# if there is anything to report then add to result
			if len(errors) > 0:
				# add result:
				results.append({"task":task, "errors":errors})

			progress_cb(100)

		return results

	def _publish_prop_for_item(self, item, output, work_template, primary_publish_path, sg_task, comment, thumbnail_path, progress_cb):
		"""
		Export an asset from the scene and publish it to Shotgun.
		"""
		assetName = item["name"]
		objectName = item["other_params"]["propName"]
		groupSelection = item["other_params"]["selectionDict"]
		assetType = item["type"]
		tank_type = output["tank_type"]
		publish_template = output["publish_template"]        
		
		filters = [ ['code', 'is', 'Prop Modeling'] ]
		taskTemplate = self.parent.shotgun.find_one('TaskTemplate', filters)
		
		# get the current scene path and extract fields from it
		# using the work template:
		scene_path = os.path.abspath(cmds.file(query=True, sn=True))
		mainFields = work_template.get_fields(scene_path)
		
		version = 1
		
		# fields needs : '@asset_root_step/work/maya/{Asset}_{Step}_v{version}.ma'
		fields = {"sg_asset_type": assetType, "Asset":assetName, "Step":"mod", "version":version}
		
		# create the publish path by applying the fields 
		# with the publish template:
		model_workfile_path = work_template.apply_fields(fields)
		
		publish_version = fields["version"] -1
		fields["version"] = publish_version
		model_publish_path = publish_template.apply_fields(fields)
		progress_cb(10)
		print "### model_publish_path = %s ###" %model_publish_path
		
		if os.path.exists(model_publish_path):
			raise TankError("The published file named '%s' already exists!" % model_publish_path)

		# Do all the resetting transformations/saving/exporting and other stuff...
		tempChildren = cmds.listRelatives(objectName, allDescendents = False, children = True, shapes = False, path = True)
		if objectName in tempChildren:
			tempChildren.remove(objectName)
		cmds.select(tempChildren, hierarchy=True, add=False)
		sel=cmds.ls(selection=True, excludeType = "transform")
		cmds.select(sel)
		
		tempPos, tempRot, tempScl = getTransform(objectName)
		setTransform(objectName)
		
		progress_cb(25)
		# print dir(self.parent)
		# print dir(self.parent.tank)
		# print dir(self.parent.shotgun)
		
		try:
			print 'TRY to publish model : %s' %objectName
			publish_folder = os.path.dirname(model_publish_path)
			workfile_folder = os.path.dirname(model_workfile_path)
			self.parent.ensure_folder_exists(publish_folder)
			self.parent.ensure_folder_exists(workfile_folder)
			
			tk = self.parent.tank
			# print 'implement the export of object :', assetName
			
			# print 'Make group and put meshes in it...'
			groupName = 'GRP_%s' %(assetName)
			groupName = cmds.group( name = groupName, world = True)
			
			# print 'Unparenting meshes for export'
			# tempChildObjects = cmds.parent(groupName, world = True)
			
			# print 'exporting meshes'
			cmds.select(groupName, hierarchy=True, add=False)
			returnName = cmds.file(model_publish_path, type='mayaAscii', exportSelected = True)
			returnWorkName = cmds.file(model_workfile_path, type='mayaAscii', exportSelected = True)
			progress_cb(45)
			
			print 'parenting meshes again...'
			cmds.parent(groupName, objectName)
			print 'export done...'
			
		except Exception, e:
			raise TankError("Failed to export model: %s" % e)
		
		progress_cb(50)
		
		# work out publish name:
		publish_name = self._get_publish_name(model_publish_path, publish_template, fields)
		print "Publish name = ", publish_name
		setTransform(objectName, tempPos, tempRot, tempScl)
		returnEntity = self._create_asset_in_shotgun(assetName, assetType, [self.parent.context.entity], template = taskTemplate)
		returnContext = self.parent.tank.context_from_entity(returnEntity["type"], returnEntity["id"])
				
		progress_cb(75)
		### Finally, register this publish with Shotgun
		returnValue = self._register_publish(model_publish_path, 
							   assetName, 
							   sg_task, 
							   publish_version, 
							   tank_type,
							   comment,
							   thumbnail_path, 
							   returnContext,
							   [primary_publish_path])

		progress_cb(90)
		### Create folders from shotgun... (= wait long time) ###
		# print self.parent.tank.preview_filesystem_structure(returnEntity["type"], returnEntity["id"], "tk-maya")
		self.parent.tank.create_filesystem_structure(returnEntity["type"], returnEntity["id"], "tk-maya")
		
		
							   
	def _register_publish(self, path, name, sg_task, publish_version, tank_type, comment, thumbnail_path, context = None, dependency_paths=None):
		"""
		Helper method to register publish using the 
		specified publish info.
		"""
		# construct args:
		args = {"tk": self.parent.tank,"context": context,"comment": comment,"path": path,"name": name,"version_number": publish_version,"thumbnail_path": thumbnail_path,"task": sg_task,"dependency_paths": dependency_paths,"published_file_type":tank_type,"user": self.parent.context.user}

		# print args
		# register publish;
		sg_data = tank.util.register_publish(**args)
		print 'Register in shotgun done!'
		
		return sg_data
	
	def _create_asset_in_shotgun(self, name, type, parents=None, template=None):
		user = self.parent.context.user
		data = {
			'project':self.parent.context.project,
			'code': name,
			'sg_asset_type': type,
			'sg_status_list':'wtg',
			'created_by': user,
			'updated_by': user,
			'parents':parents,
			'task_template':template
			}
		
		return self.parent.shotgun.create("Asset", data)
	
	def _get_publish_name(self, path, template, fields=None):
		"""
		Return the 'name' to be used for the file - if possible
		this will return a 'versionless' name
		"""
		# first, extract the fields from the path using the template:
		fields = fields.copy() if fields else template.get_fields(path)
		if "name" in fields and fields["name"]:
			# well, that was easy!
			name = fields["name"]
		else:
			# find out if version is used in the file name:
			template_name, _ = os.path.splitext(os.path.basename(template.definition))
			version_in_name = "{version}" in template_name
		
			# extract the file name from the path:
			name, _ = os.path.splitext(os.path.basename(path))
			delims_str = "_-. "
			if version_in_name:
				# looks like version is part of the file name so we        
				# need to isolate it so that we can remove it safely.  
				# First, find a dummy version whose string representation
				# doesn't exist in the name string
				version_key = template.keys["version"]
				dummy_version = 9876
				while True:
					test_str = version_key.str_from_value(dummy_version)
					if test_str not in name:
						break
					dummy_version += 1
				
				# now use this dummy version and rebuild the path
				fields["version"] = dummy_version
				path = template.apply_fields(fields)
				name, _ = os.path.splitext(os.path.basename(path))
				
				# we can now locate the version in the name and remove it
				dummy_version_str = version_key.str_from_value(dummy_version)
				
				v_pos = name.find(dummy_version_str)
				# remove any preceeding 'v'
				pre_v_str = name[:v_pos].rstrip("v")
				post_v_str = name[v_pos + len(dummy_version_str):]
				
				if (pre_v_str and post_v_str 
					and pre_v_str[-1] in delims_str 
					and post_v_str[0] in delims_str):
					# only want one delimiter - strip the second one:
					post_v_str = post_v_str.lstrip(delims_str)

				versionless_name = pre_v_str + post_v_str
				versionless_name = versionless_name.strip(delims_str)
				
				if versionless_name:
					# great - lets use this!
					name = versionless_name
				else: 
					# likely that version is only thing in the name so 
					# instead, replace the dummy version with #'s:
					zero_version_str = version_key.str_from_value(0)        
					new_version_str = "#" * len(zero_version_str)
					name = name.replace(dummy_version_str, new_version_str)
		
		return name     
			
		
def setTransform(objName, pos = [0,0,0], rot = [0,0,0], scl = [1,1,1], visibility = True):
	cmds.setAttr("%s.translateX" %objName, pos[0])
	cmds.setAttr("%s.translateY" %objName, pos[1])
	cmds.setAttr("%s.translateZ" %objName, pos[2])

	cmds.setAttr("%s.rotateX" %objName, rot[0])
	cmds.setAttr("%s.rotateY" %objName, rot[1])
	cmds.setAttr("%s.rotateZ" %objName, rot[2])

	cmds.setAttr("%s.scaleX" %objName, scl[0])
	cmds.setAttr("%s.scaleY" %objName, scl[1])
	cmds.setAttr("%s.scaleZ" %objName, scl[2])

def getTransform(objName):
	pos = [cmds.getAttr("%s.translateX" %objName),cmds.getAttr("%s.translateY" %objName),cmds.getAttr("%s.translateZ" %objName)]
	rot = [cmds.getAttr("%s.rotateX" %objName),cmds.getAttr("%s.rotateY" %objName),cmds.getAttr("%s.rotateZ" %objName)]
	scl = [cmds.getAttr("%s.scaleX" %objName),cmds.getAttr("%s.scaleY" %objName),cmds.getAttr("%s.scaleZ" %objName)]

	return pos, rot, scl
	