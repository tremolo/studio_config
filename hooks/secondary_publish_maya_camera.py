# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import time, datetime, os, subprocess
import shutil
import maya.cmds as cmds

from os import listdir
from os.path import isfile, join

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
		def FindFirstImageOfSequence(FolderPath):
			ImgsList=[]
			for file in (os.listdir(FolderPath)):
				SeqImgName = str.split(str(file),".")[1]
				ImgsList.append(SeqImgName)
			First_elmnt=ImgsList[0]
			return First_elmnt
			
		def FindFirstImageOfSequence(FolderPath):
			ImgsList=[]
			for file in (os.listdir(FolderPath)):
				if file.endswith(".png"):
					SeqImgName = str.split(str(file),".")[1]
					ImgsList.append(int(SeqImgName))
				First_elmnt=ImgsList[0]
			return First_elmnt

		def FindLastImageOfSequence(FolderPath):
			ImgsList=[]
			for file in (os.listdir(FolderPath)):
				if file.endswith(".png"):
					SeqImgName = str.split(str(file),".")[1]
					ImgsList.append(int(SeqImgName))
				Last_elmnt=ImgsList[-1]
			return Last_elmnt
			
		def FindLengthOfSequence(FolderPath):
			ImgsList=[]
			for file in (os.listdir(FolderPath)):
				if file.endswith(".png"):
					SeqImgName = str.split(str(file),".")[1]
					ImgsList.append(int(SeqImgName))
				Length_seq=len(ImgsList)
			return Length_seq
			
		def MakeListOfSequence(FolderPath):
			ImgsList=[]
			for file in (os.listdir(FolderPath)):
				if file.endswith(".png"):
					SeqImgName = str.split(str(file),".")[1]
					ImgsList.append(int(SeqImgName))
			return ImgsList

		def FindMissingFramesFromSequence(SequenceSet,inputStart,inputEnd):
			# my_list= list(range( int(FindFirstImageOfSequence(os.path.dirname(RenderPath)))	, int(FindLastImageOfSequence(os.path.dirname(RenderPath)))	 ))
			my_list= list(range( inputStart, inputEnd))
			MissingFrames =  set(my_list)-set(SequenceSet)
			return sorted(MissingFrames)
			
		def combineMediaFiles(fileList,output,concatTxt=None, ffmpeg_path = "ffmpeg"):
			rootPath = str.split(str(fileList[0]),"/q")[0]
			mediaType = str.rsplit(str(fileList[0]),".",1)[1]
			mediaFilePresent = False
			mediaListFile = rootPath+'/tmp_'+mediaType+'List.txt'
			if concatTxt != None:
				mediaListFile = concatTxt
			with open(mediaListFile, 'w') as mediaTxtFile:
				for mediaFile in fileList:
					if os.path.exists(mediaFile):
						mediaFilePresent = True
						#print mediaFile
						shotPath = str.split(str(mediaFile),"Sequences")[1][1:]
						if concatTxt != None:
							shotPath = str.split(str(mediaFile),os.path.dirname(concatTxt))[1][1:]
						mediaTxtFile.write("file '" +shotPath+"'")
						mediaTxtFile.write('\r\n')
					else:
						print("AUDIO FILE NOT FOUND :  " + str(mediaFile))
						results.append({"task":"audio stuff", "errors":("AUDIO FILE NOT FOUND :  " + str(mediaFile))})
			if mediaFilePresent:
				command = os.path.normpath(ffmpeg_path + ' -f concat -i '+mediaListFile+' -c copy '+output)
				command = str.replace(str(command), "\\" , "/")
				#print command
				value = subprocess.call(command)
				return output
			else:
				return None
		def findLastVersion(FolderPath):
			fileList=os.listdir(FolderPath)
			fileList.sort()
			lastVersion = fileList[-1]
			return str(FolderPath+"/"+lastVersion)


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
		CutInList = []
		# these booleans can be used for 
		noOverscan = False
		resetCutIn = False

		# template stuff...
		# tk = tank.tank_from_path("W:/RTS/Tank/config")
		tk = self.parent.tank
		scenePath = cmds.file(q=True,sceneName=True)
		scene_template = tk.template_from_path(scenePath)
		flds = scene_template.get_fields(scenePath)
		flds['width'] = 1724
		flds['height'] = 936
		pb_template = tk.templates["maya_seq_playblast_publish"]
		pb_template_current = tk.templates["maya_seq_playblast_current"]
		pbArea_template = tk.templates["maya_seq_playblast_publish_area"]
		audio_template = tk.templates["shot_published_audio"]
		mov_template = tk.templates["maya_seq_playblast_publish_currentshots_mov"]
		concatMovTxt = tk.templates["maya_seq_playblast_publish_concatlist"]
		pbMov = tk.templates["maya_seq_playblast_publish_mov"]
		pbMp4 = tk.templates["maya_seq_playblast_review_mp4"]

		# get extra shot info through shotgun
		fields = ['id']
		sequence_id = self.parent.shotgun.find('Sequence',[['code', 'is',flds['Sequence'] ]], fields)[0]['id']
		fields = ['id', 'code', 'sg_asset_type','sg_cut_order','sg_cut_in','sg_cut_out']
		filters = [['sg_sequence', 'is', {'type':'Sequence','id':sequence_id}]]
		assets= self.parent.shotgun.find("Shot",filters,fields)
		results = []

		for task in tasks:
			item = task["item"]
			output = task["output"]
			errors = []
			
			#get shots from scan scene
			if item["type"] == "shot":
				shotTask = [item["name"]][0]
				pbShots += [shotTask]
			# get corresponding cut in values from shotgun
				for sht in assets:
					shot_from_shotgun = str.split(sht['code'],"_")[1]
					if shot_from_shotgun == shotTask:
						CutInList += [sht['sg_cut_in']]
			
			# set extra settings
			if item["type"] == "setting":
				if item["name"]=="overscan":
					noOverscan = True
				if item["name"]=="set Cut in":
					resetCutIn = True

			# if there is anything to report then add to result
			if len(errors) > 0:
				# add result:
				results.append({"task":task, "errors":errors})

		# temporarily hide cams and curves
		modPan = cmds.getPanel(type="modelPanel")
		for pan in modPan:
			cmds.modelEditor( pan,e=True, alo= False, polymeshes =True )
			cmds.modelEditor( pan,e=True,displayAppearance="smoothShaded")

		CamsList = cmds.listCameras()
		for Cam in CamsList:
			cmds.camera(Cam, e=True, dr=True, dgm=True,ovr=1.3)
		
		# audio stuff
		stepVersion = flds['version']
		audioList = []
		for sht in shots:
			#print sht
			flds['Shot'] = (flds['Sequence']+"_"+sht)
			#flds['version'] = 1 #temporary set version to 1 for soundfiles ...
			audioList += [str.replace(str(audio_template.apply_fields(flds)),"\\","/")]
		flds['Shot'] = flds['Sequence']
		flds['version'] = stepVersion #set version back

		#Get USER
		USER = sgtk.util.get_current_user(tk)

		ffmpegPath = '"'+os.environ.get('FFMPEG_PATH')
		if "ffmpeg.exe" not in ffmpegPath:
			ffmpegPath += "\\ffmpeg.exe"
		ffmpegPath += '"'

		
		audioOutput = pbArea_template.apply_fields(flds)+"/"+flds['Sequence']+"_"+flds['Step']+".wav"
		combinedAudio = combineMediaFiles(audioList,audioOutput, ffmpeg_path = ffmpegPath)
		print ("combined audio at  " + audioOutput)
		

		Test = True;
		#Test = False;
		if Test:
			j = 0
			RenderPath = ""
			for pbShot in pbShots:
				CutIn = CutInList[j]
				j += 1
				
				sequenceName = flds ['Sequence']
				shotName = pbShot
				
				# ... correct this in the templates?
				flds['Shot'] = flds['Sequence']+"_"+pbShot

				#get camera name from sequence shot 
				shotCam = cmds.shot(pbShot, q=True, currentCamera=True)

				# overscanValue = cmds.getAttr(shotCam+".overscan")
				cmds.setAttr(shotCam+".overscan", 1.3)
				if noOverscan:
					cmds.setAttr(shotCam+".overscan", 1)
				
				# make outputPaths from templates
				RenderPath = pb_template.apply_fields(flds)
				pbPath = str.split(str(RenderPath),".")[0]

				renderPathCurrent = pb_template_current.apply_fields(flds)
				pbPathCurrent = str.split(str(renderPathCurrent),".")[0]
				#renderPathCurrent = str.rsplit(str(renderPathCurrent),"\\",1)[0]

				if not os.path.exists(os.path.dirname(pbPathCurrent)):
					os.makedirs(os.path.dirname(pbPathCurrent))

				pbPathCurrentMov = mov_template.apply_fields(flds)

				if not os.path.exists(os.path.dirname(pbPathCurrentMov)):
					os.makedirs(os.path.dirname(pbPathCurrentMov))

				# report progress:
				progress_cb(0, "Publishing", task)

				shotStart = cmds.shot(pbShot,q=True,sequenceStartTime=True)
				shotEnd = cmds.shot(pbShot,q=True,sequenceEndTime=True)
				progress_cb(25, "Making playblast %s" %pbShot)
				cmds.playblast(indexFromZero=False,filename=(pbPath),fmt="iff",compression="png",wh=(flds['width'], flds['height']),startTime=shotStart,endTime=shotEnd,sequenceTime=1,forceOverwrite=True, clearCache=1,showOrnaments=1,percent=100,offScreen=True,viewer=False,useTraxSounds=True)
				progress_cb(50, "Placing Slates %s" %pbShot)
				
				Film = "Richard the Stork"
				#GET CURRENT DATE
				today = datetime.date.today()
				todaystr = today.isoformat()
				
				"""
					Adding Slates to playblast files
				"""
				for i in range(int(shotStart),int(shotEnd)+1):
					FirstPartName = RenderPath.split( '%04d' )[0]
					EndPartName = '%04d' % i + RenderPath.split( '%04d' )[-1]
					ImageFullName = FirstPartName + EndPartName
					pbFileCurrent = pbPathCurrent+"."+EndPartName
					ffmpeg.ffmpegMakingSlates(inputFilePath= ImageFullName, outputFilePath= ImageFullName, topleft = flds ['Sequence']+"_"+flds['Step']+"_v"+str('%03d' % (flds['version'])), topmiddle = Film, topright = str(int(CutIn))+"-"+str('%04d' %(i-int(shotStart)+CutIn))+"-"+str('%04d' %(int(shotEnd)-int(shotStart)+CutIn))+"  "+str('%04d' %(i-int(shotStart)))+"-"+str('%04d' %(int(shotEnd)-int(shotStart))), bottomleft = shotName, bottommiddle = USER['name'], bottomright = todaystr , ffmpegPath =ffmpegPath, font = "C:/Windows/Fonts/arial.ttf"  )
					print("COPYING PNG "+ImageFullName+"  TO  "+pbFileCurrent+"  FOR SHOT  " + shotName)
					shutil.copy2(ImageFullName, pbFileCurrent)
				
				shotAudio = audio_template.apply_fields(flds)
				shotAudio = findLastVersion(os.path.dirname(shotAudio))
				print ffmpeg.ffmpegMakingMovie(inputFilePath=renderPathCurrent, outputFilePath=pbPathCurrentMov, audioPath=shotAudio, start_frame=int(shotStart),end_frame=int(shotEnd), framerate=24 , encodeOptions='libx264',ffmpegPath=ffmpegPath)
				# end_frame=shotEnd

			sequenceTest= MakeListOfSequence(os.path.dirname(RenderPath))
			FistImg= int(FindFirstImageOfSequence(os.path.dirname(RenderPath))) 
			LastImg= int(FindLastImageOfSequence(os.path.dirname(RenderPath)))

			FramesMissingList= FindMissingFramesFromSequence( sequenceTest , FistImg, LastImg )
						
			"""
				Copy empty frames
			"""
			blackFrame = False
			blackFrameName = ""
			for n in FramesMissingList:
				if blackFrame == False:
					blackFrameName = FirstPartName+str('%04d' % n)+".png"
					value = subprocess.call('%s -f lavfi -i color=c=black:s="%s" -vframes 1 "%s"' %(ffmpegPath,(str(flds['width'])+"x"+ str(flds['height'])),FirstPartName+str('%04d' % n)+".png"))
					print '%s -f lavfi -i color=c=black:s="%s" -vframes 1 "%s"' %(ffmpegPath,(str(flds['width'])+"x"+ str(flds['height'])),FirstPartName+str('%04d' % n)+".png")
					blackFrame = True
				
				newFrameName = FirstPartName+str('%04d' % n)+".png"
				if blackFrameName != newFrameName:
					shutil.copy2(blackFrameName, newFrameName)	

			FirstImageNumber= FindFirstImageOfSequence(os.path.dirname(RenderPath))
			FirstImageNumberSecond= FirstImageNumber/24

			'''
			makeSeqMov
			'''
			concatTxt = concatMovTxt.apply_fields(flds)
			pbMovPath = pbMov.apply_fields(flds)
			pbMp4Path = pbMp4.apply_fields(flds)

			movList = []
			for mov in os.listdir(os.path.dirname(pbPathCurrentMov)):
				movList += [os.path.dirname(pbPathCurrentMov)+"/"+mov]
			print movList

			makeSeqMov = True
			if makeSeqMov:
				if not os.path.exists(os.path.dirname(pbMovPath)):
					os.makedirs(os.path.dirname(pbMovPath))
				
				if not os.path.exists(os.path.dirname(pbMp4Path)):
					os.makedirs(os.path.dirname(pbMp4Path))
				"""
					SEQUENCE MOV and MP4 Creation
				"""
				print "Making mov and mp4: \n", pbMovPath, ' --- ', pbMp4Path
				print combineMediaFiles(movList,pbMovPath,concatTxt)
				print combineMediaFiles(movList,pbMp4Path,concatTxt)
		
				# ----------------------------------------------
				# UPLOAD QUICKTIME
				# ----------------------------------------------
				upload = True
				if upload:
					SERVER_PATH = 'https://rts.shotgunstudio.com'
					SCRIPT_USER = 'AutomateStatus_TD'
					SCRIPT_KEY = '8119086c65905c39a5fd8bb2ad872a9887a60bb955550a8d23ca6c01a4d649fb'

					sg = sgtk.api.shotgun.Shotgun(SERVER_PATH, SCRIPT_USER, SCRIPT_KEY)
					user = self.parent.context.user
					
					data = {'project': {'type':'Project','id':66},
							'entity': {'type':'Sequence', 'id':int(sequence_id)},
							'code': flds ['Sequence']+"_"+flds['Step']+"_v"+str('%03d' % (flds['version'])),
							'sg_path_to_frames':os.path.dirname(RenderPath),
							'sg_path_to_movie':pbMovPath,
							'created_by': user,
							'updated_by': user
							}

					result = sg.create('Version', data)
					executed = sg.upload("Version",result['id'],pbMovPath,'sg_uploaded_movie')
					print executed
			
			# print "TODO : make mov of whole sequence with audio"
			return results

