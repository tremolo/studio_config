# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Hook that gets executed when the current user is being retrieved.

"""
from tank import Hook
from tank_vendor.shotgun_api3 import Shotgun
import os, sys
 
class GetCurrentLogin(Hook):
	
	def execute(self, **kwargs):
		"""
		Return the login name for the user currently logged in. This is typically used
		by Toolkit to resolve against the 'login' field in the Shotgun users table in order
		to extract further metadata.
		"""
		if sys.platform == "win32": 
			local_username = os.environ.get("USERNAME", None)
		else:
			local_username = os.environ.get("USER", None)
		
			# http://stackoverflow.com/questions/117014/how-to-retrieve-name-of-current-windows-user-ad-or-local-using-python
		if os.environ.get("USERNAMESHOTGUN", None) == None:
			# return os.environ.get("USERNAME", None)
			script_name = "User_Activity"
			script_api_key = "8323196ca1dfe1aee8ec00e0b885dbae9ab02f3144daf19cd23897c85ba168d2"
			shotgun_link = 'https://rts.shotgunstudio.com'

			sg = Shotgun(shotgun_link, script_name, script_api_key)

			fields = [ 'login','tag_list' ]
			filters = [ [ 'login', 'is', local_username ] ]
			filters_alt = [ [ 'tag_list', 'is', local_username ] ]
			humanuser = sg.find_one( "HumanUser", filters, fields )
			humanuser_alt = sg.find_one( "HumanUser", filters_alt, fields )

			# If local user match with shotgun user
			if humanuser:
				return local_username
			# If local user match with shotgun alternative user
			elif humanuser_alt:
				return humanuser_alt['login']

		else:
			return os.environ.get("USERNAMESHOTGUN", None)