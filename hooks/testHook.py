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

class testHook(Hook):
	def execute(self):
		wtd_fw = self.load_framework("tk-framework-wtd_v0.x.x")
		actions = wtd_fw.import_module("maya.actions")

		actions.testDef("sdgfsdgssssssssssssss")



		




