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

import tempfile
import uuid
import re
from itertools import chain

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
		scene_template = self.parent.sgtk.template_from_path(scene_path)
		if not work_template.validate(scene_path):
			scene_template = self.parent.sgtk.template_from_path(scene_path)
			fields = scene_template.get_fields(scene_path)
			if not "version" in fields:
				raise TankError("File '%s' is not a valid path, unable to publish!" % scene_path)
		else:
			scene_template = work_template
			
		layers = doc.artLayers
		layerSets = doc.layerSets
		layers = [layers.index(i) for i in xrange(layers.length)]
		layerSets = [layerSets.index(i) for i in xrange(layerSets.length)]
		
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
			progress_cb(0, "Start Publishing", task)
			if itemType == "pngLayer" or itemType == "exrLayer":
				# for i in layersDict:
					# layersDict[i].visible = False
					
				# publish item here, e.g.
				try:
					errors = self.publish_layer_as_image(name=i, task=task, work_template=scene_template, publish_template=publish_template, primary_publish_path=primary_publish_path, sg_task=sg_task, comment=comment, progress_cb=progress_cb)
				except Exception, e:
					errors.append("Don't know how to publish this item! %s" %e)   
					errors.append(message)   

			# if there is anything to report then add to result
			if len(errors) > 0:
				# add result:
				results.append({"task":task, "errors":errors})
			 
			progress_cb(100)
			 
		# for(i, layer) in enumerate(layers):
			# layer.visible = original_visibility_layers[i]
		# for(i, layerSet) in enumerate(layerSets):
			# layerSet.visible = original_visibility_layerSets[i]
			 
		return results

	def publish_layer_as_image(self, name, task, work_template, publish_template, primary_publish_path, sg_task, comment, progress_cb):
		"""
		Publish the specified layer as image (png/exr/...)
		"""
		errors = []
		MAX_THUMB_SIZE = 256

		# generate the export path using the correct template together
		# with the fields extracted from the work template:
		export_path = None
		active_doc = photoshop.app.activeDocument
		scene_path = active_doc.fullName.nativePath
		item = task["item"]
		layer_name = item["name"]
		itemType = item["type"]
		output = task["output"]
		other = item["other_params"]
		publish_template = output["publish_template"]
		errors = []
		fields = None
		message = ""
		# publish type will be driven from the layer name:
		publish_type = other["tank_type"]
		
		progress_cb(10, "Building output path")
		
		try:
			fields = work_template.get_fields(scene_path)
			fields = dict(chain(fields.items(), self.parent.context.as_template_fields(publish_template).items()))
			fields["TankType"] = publish_type
			fields["channel"] = other["targetName"]
			# fields["layer_short_name"] = layer_short_name            
			
			export_path = publish_template.apply_fields(fields).encode("utf8")
		except TankError, e:
			errors.append("Failed to construct export path for layer '%s': %s" % (layer_name, e))
			return errors

		# ensure the export folder exists:
		export_folder = os.path.dirname(export_path)
		self.parent.ensure_folder_exists(export_folder)

		# get a path in the temp dir to use for the thumbnail:
		thumbnail_path = os.path.join(tempfile.gettempdir(), "%s_sgtk.png" % uuid.uuid4().hex)

		# set unit system to pixels:
		original_ruler_units = photoshop.app.preferences.rulerUnits
		pixel_units = photoshop.StaticObject('com.adobe.photoshop.Units', 'PIXELS')
		photoshop.app.preferences.rulerUnits = pixel_units        
			
		try:
			orig_name = active_doc.name
			width_str = active_doc.width
			height_str = active_doc.height
			
			# calculate the thumbnail doc size:
			doc_width = doc_height = 0
			exp = re.compile("^(?P<value>[0-9]+) px$")
			mo = exp.match (width_str)
			if mo:
				doc_width = int(mo.group("value"))
			mo = exp.match (height_str)
			if mo:
				doc_height = int(mo.group("value"))
	
			thumb_width = thumb_height = 0
			if doc_width and doc_height:
				max_sz = max(doc_width, doc_height)
				if max_sz > MAX_THUMB_SIZE:
					scale = min(float(MAX_THUMB_SIZE)/float(max_sz), 1.0)
					thumb_width = max(min(int(doc_width * scale), doc_width), 1)
					thumb_height = max(min(int(doc_height * scale), doc_height), 1)
			
			# set up the export options and get a file object:
			layer_file = photoshop.RemoteObject('flash.filesystem::File', export_path)     
			
			file_save_options = None
			if export_path.endswith(".png"):
				file_save_options = photoshop.RemoteObject('com.adobe.photoshop::PNGSaveOptions')
			elif export_path.endswith(".exr"):
				"""
				TODO EXR STUFF!!!
				"""
				print 'TODO, create exr stuff'
				errors.append("Can not publish to EXR yet %s" %export_path)
				return errors
				file_save_options = photoshop.RemoteObject('com.adobe.photoshop::ExrSaveOptions')
			else:
				errors.append("Can not publish to %s" %export_path)
				return errors
			
			# set up the thumbnail options and get a file object:
			thumbnail_file = photoshop.RemoteObject('flash.filesystem::File', thumbnail_path)
			png_save_options = photoshop.RemoteObject('com.adobe.photoshop::PNGSaveOptions')
			
			close_save_options = photoshop.flexbase.requestStatic('com.adobe.photoshop.SaveOptions', 'DONOTSAVECHANGES')              
			
			progress_cb(20, "Exporting %s layer" % layer_name)
			
			# duplicate doc
			doc_name, doc_sfx = os.path.splitext(orig_name)
			layer_doc_name = "%s_%s.%s" % (doc_name, layer_name, doc_sfx)            
			layer_doc = active_doc.duplicate(layer_doc_name)
			try:
				# set layer visibility
				layers = layer_doc.artLayers
				for layer in [layers.index(li) for li in xrange(layers.length)]:
					layer.visible = (layer.name == layer_name)
				
				# flatten
				layer_doc.flatten()
				
				# save:
				layer_doc.saveAs(layer_file, file_save_options, True)
				
				progress_cb(60, "Exporting thumbnail")
				
				# resize for thumbnail
				if thumb_width and thumb_height:
					layer_doc.resizeImage("%d px" % thumb_width, "%d px" % thumb_height)                  
				
				# save again (as thumbnail)
				layer_doc.saveAs(thumbnail_file, png_save_options, True)
				
			finally:
				# close the doc:
				layer_doc.close(close_save_options)
			
			name = os.path.basename(export_path)
			progress_cb(85, "Publishing %s" %name)
			tank_publish = self._register_publish(path=export_path, name=name, sg_task=sg_task, publish_version=fields["version"], tank_type=publish_type, comment=comment, thumbnail_path=thumbnail_path, context=self.parent.context, dependency_paths=[primary_publish_path])
			
		finally:
			# delete the thumbnail file:
			if os.path.exists(thumbnail_path):
				try:
					os.remove(thumbnail_path)
				except:
					pass
			
			# set units back to original
			photoshop.app.preferences.rulerUnits = original_ruler_units

		return errors
		
		
	def _register_publish(self, path, name, sg_task, publish_version, tank_type, comment, thumbnail_path, context = None, dependency_paths=None):
		"""
		Helper method to register publish using the 
		specified publish info.
		"""
		user = self.parent.context.user
		# construct args:
		args = {
			"tk": self.parent.tank,"context": context,"comment": comment,"path": path,
			"name": name,"version_number": publish_version,"thumbnail_path": thumbnail_path,
			"task": sg_task,"dependency_paths": dependency_paths,"published_file_type":tank_type,
			"user": user,"created_by": user,"updated_by": user
		}
		sg_data = tank.util.register_publish(**args)
		
		print 'Register in shotgun done!'
		
		return sg_data
	
	"""
	Extra function to publish thumbnail from photoshop.
	"""
		
	def create_thumbnail(self, name = "", targetpath = None, MAX_THUMB_SIZE = 256):
		errors = []
		
		if name == "":
			name = "thumbDouble"
		
		# get a path in the temp dir to use for the thumbnail:
		thumbnail_path = ""
		if targetpath != None:
			thumbnail_path = targetpath
		else:
			thumbnail_path = os.path.join(tempfile.gettempdir(), "%s_sgtk.png" % uuid.uuid4().hex)

		# set unit system to pixels:
		original_ruler_units = photoshop.app.preferences.rulerUnits
		pixel_units = photoshop.StaticObject('com.adobe.photoshop.Units', 'PIXELS')
		photoshop.app.preferences.rulerUnits = pixel_units        

		try:
			active_doc = photoshop.app.activeDocument
			orig_name = active_doc.name
			width_str = active_doc.width
			height_str = active_doc.height
			
			# calculate the thumbnail doc size:
			doc_width = doc_height = 0
			exp = re.compile("^(?P<value>[0-9]+) px$")
			mo = exp.match (width_str)
			if mo:
				doc_width = int(mo.group("value"))
			mo = exp.match (height_str)
			if mo:
				doc_height = int(mo.group("value"))
	
			thumb_width = thumb_height = 0
			if doc_width and doc_height:
				max_sz = max(doc_width, doc_height)
				if max_sz > MAX_THUMB_SIZE:
					scale = min(float(MAX_THUMB_SIZE)/float(max_sz), 1.0)
					thumb_width = max(min(int(doc_width * scale), doc_width), 1)
					thumb_height = max(min(int(doc_height * scale), doc_height), 1)
					
			# set up the thumbnail options and get a file object:
			thumbnail_file = photoshop.RemoteObject('flash.filesystem::File', thumbnail_path)
			png_save_options = photoshop.RemoteObject('com.adobe.photoshop::PNGSaveOptions')
			
			close_save_options = photoshop.flexbase.requestStatic('com.adobe.photoshop.SaveOptions', 'DONOTSAVECHANGES')              
			
			# duplicate doc
			doc_name, doc_sfx = os.path.splitext(orig_name)
			thumb_doc_name = "%s_%s.%s" % (doc_name, name, doc_sfx)            
			thumb_doc = active_doc.duplicate(thumb_doc_name)
			try:
				# flatten
				thumb_doc.flatten()
				
				# resize for thumbnail
				if thumb_width and thumb_height:
					thumb_doc.resizeImage("%d px" % thumb_width, "%d px" % thumb_height)
				
				# save again (as thumbnail)
				thumb_doc.saveAs(thumbnail_file, png_save_options, True)
			finally:
				# close the doc:
				thumb_doc.close(close_save_options)	
		except:
			errors.append("Failed to construct thumbnail for '%s': %s" % (name, e))
			return errors
		
		return thumbnail_path
		
