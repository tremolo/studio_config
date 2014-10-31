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

        def isCamSelected(shotName):
            camList = []
            selectetShots = []
            for cam in cmds.ls(sl=True):
                par = cmds.listRelatives(cam,parent=True,fullPath=True)
                if par != None:
                    cam = str.split(str(par[0]),'|')[1]
                if cam not in camList:
                    camList += [cam]
                    selectetShots += [str.split(str(cam),'_')[-1]]
            result = False
            if shotName in selectetShots:
                result = True
            return (result)
        items = []
        
        # get the main scene:
        scene_name = cmds.file(query=True, sn=True)
        if not scene_name:
            raise TankError("Please Save your file before Publishing")
        
        scene_path = os.path.abspath(scene_name)
        name = os.path.basename(scene_path)

        # create the primary item - this will match the primary output 'scene_item_type':            
        items.append({"type": "work_file", "name": name})

        tk = self.parent.tank
        scenePath = cmds.file(q=True,sceneName=True)
        scene_template = tk.template_from_path(scenePath)
        flds = scene_template.get_fields(scenePath)

        # get shotgun info about what shot are needed in this sequence
        fields = ['id']
        sequence_id = self.parent.shotgun.find('Sequence',[['code', 'is',flds['Sequence']]], fields)[0]['id']
        fields = ['id', 'code', 'sg_asset_type','sg_cut_in','sg_cut_out']
        filters = [['sg_sequence', 'is', {'type':'Sequence','id':sequence_id}]]
        assets= self.parent.shotgun.find("Shot",filters,fields)
        sg_shots=[]
        for sht in assets:
            sg_shots += [str.split(sht['code'],"_")[1]]

        # define used cameras and shots in the camera sequencer
        shots = cmds.ls(type="shot")
        shotCams = []
        unUsedCams = []
        items.append({"type": "setting","name": "NO overscan","description": "set overscan Value to 1(no extra space used)","selected":False})
        items.append({"type": "setting","name": "set Cut in","description": "set Cut in to 1001 for each individual shot","selected":False})
        for sht in shots:
            shotCam = cmds.shot(sht, q=True, currentCamera=True)
            shotCams += [shotCam]
            select = True
            if cmds.ls(sl=True) != []:
                select = isCamSelected(sht)

            if sht not in sg_shots:
                items.append({"type": "shot","name": sht,"description":"!!! shot not in shotgun  ->  "+shotCam,"selected":select})
            else:
                items.append({"type": "shot","name": sht,"description":"    "+shotCam,"selected":select})

            #print shotCam
        
        for sg_shot in sg_shots:
            if sg_shot not in shots:
                print(sg_shot+" cam is not in scene...")
                items.append({"type": "shot","name": sg_shot,"description": "!!! missing shot? check shotgun  ->  ","selected":False})

        return items
