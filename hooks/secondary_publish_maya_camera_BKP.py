# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import time, datetime, os
import shutil
import maya.cmds as cmds

import tank
from tank import Hook
from tank import TankError

import sgtk
from sgtk.platform import Application


#from shotgun import Shotgun

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

		wtd_fw = self.load_framework("tk-framework-wtd_v0.x.x")
		ffmpeg = wtd_fw.import_module("pipeline.ffmpeg")
		# ffmpeg.test()
		
		shots = cmds.ls(type="shot")
		shotCams = []
		unUsedCams = []

		for sht in shots:
			shotCam = cmds.shot(sht, q=True, currentCamera=True)
			shotCams += [shotCam]
			#print shotCam

		pbShots = []


		results = []
		# publish all tasks:
		for task in tasks:
			item = task["item"]
			output = task["output"]
			errors = []

			print item

			# publish item here, e.g.
			#if output["name"] == "playblast":
			if item["type"] == "shot":
				pbShots += [item["name"]]
			else:
				errors.append("Don't know how to publish this item!")   

			# if there is anything to report then add to result
			if len(errors) > 0:
				# add result:
				results.append({"task":task, "errors":errors})
			 
		
		print("shots to playblast = " + str(pbShots))

		# set extra settings
		noOverscan = False
		resetCutIn = False
		if item["type"] == "setting":
			if [item["name"]]=="overscan" and [item["selected"]]:
				noOverscan = True
			if [item["name"]]=="set Cut in" and [item["selected"]]:
				resetCutIn = True


		# template stuff...
		tk = tank.tank_from_path("W:/RTS/Tank/config")   

		scenePath = cmds.file(q=True,sceneName=True)
		scene_template = tk.template_from_path(scenePath)

		flds = scene_template.get_fields(scenePath)
		
		flds['width'] = 1734
		flds['height'] = 936 
		
		#flds['SEQ'] = flds['Sequence']
		#flds['name'] = ""
		
		pb_template = tk.templates["maya_seq_playblast"]

	#cmds.playblast(fmt="avi",startTime=pbStart,endTime=pbEnd,sequenceTime=1,forceOverwrite=True, filename="W:/RTS/People/xander/camera_sequencer/Shot.avi",clearCache=1,showOrnaments=0,percent=100,wh=(1724, 936),offScreen=True,viewer=1,useTraxSounds=True,compression="MS-RLE",quality=100)
		for pbShot in pbShots:
			flds['Shot'] = pbShot
			flds['name'] = (pbShot+"_"+flds['Step'])
			shotCam = cmds.shot(pbShot, q=True, currentCamera=True)
			overscanValue = cmds.getAttr(shotCam+".overscan")
			if noOverscan:
				cmds.setAttr(shotCam+".overscan", 1)
			
			pbPath = pb_template.apply_fields(flds)
			pbPath = str.split(str(pbPath),".")[0]
			ffmpegPath = pb_template.apply_fields(flds)
			# report progress:
			progress_cb(0, "Publishing", task)

			shotStart = cmds.shot(pbShot,q=True,sequenceStartTime=True)
			shotEnd = cmds.shot(pbShot,q=True,sequenceEndTime=True)
			progress_cb(25, "Making playblast %s" %pbShot)
			cmds.playblast(indexFromZero=resetCutIn,filename=(pbPath),fmt="iff",compression="png",wh=(flds['width'], flds['height']),startTime=shotStart,endTime=shotEnd,sequenceTime=1,forceOverwrite=True, clearCache=1,showOrnaments=0,percent=100,offScreen=True,viewer=False,useTraxSounds=True)
			progress_cb(50, "Placing Slates %s" %pbShot)
			
			cmds.setAttr(shotCam+".overscan", overscanValue)
			Film = "Richard the Stork"
			#GET CURRENT DATE
			today = datetime.date.today()
			todaystr = today.isoformat()
			#Get USER
			USER = sgtk.util.get_current_user(tk)
						
			for i in range(int(shotStart),int(shotEnd)+1):
				FirstPartName = ffmpegPath.split( '%04d' )[0]
				EndPartName = ffmpegPath.split( '%04d' )[-1]
				ImageFullName= FirstPartName + '%04d' % i + EndPartName
				ffmpeg.ffmpegMakingSlates(inputFilePath= ImageFullName,outputFilePath= ImageFullName, topleft = flds['Sequence']+"_"+pbShot+"_v"+str(flds['version']), topmiddle = Film, topright = str(int(shotStart))+"-"+str('%04d' % i)+"-"+str(int(shotEnd))+"__"+str('%04d' %(i-int(shotStart)))+"-"+str('%04d' %(int(shotEnd)-int(shotStart))), bottomleft = flds['Step'], bottommiddle = USER['name'], bottomright = todaystr , ffmpegPath =r"W:/WG/WTD_Code/trunk/wtd/pipeline/resources/ffmpeg/bin/ffmpeg.exe", font = "/Windows/Fonts/arial.ttf"  )
				
			# def ffmpegMakingSlates(inputFilePath, outputFilePath, audioPath = "", topleft = "", topmiddle = "", topright = "", bottomleft = "", bottommiddle = "", bottomright = "", ffmpegPath = "ffmpeg.exe", font = "arial.ttf", font_size = 10, font_color = "gray", slate_height = 13, slate_color = "black@0.8", overwrite = True):

		print "TODO : make mov of whole sequence with audio"
		return results




		



