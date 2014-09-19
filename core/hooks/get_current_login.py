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
			# http://stackoverflow.com/questions/117014/how-to-retrieve-name-of-current-windows-user-ad-or-local-using-python
			if os.environ.get("USERNAMESHOTGUN", None) == None:
				# return os.environ.get("USERNAME", None)
				script_name = "User_Activity"
				script_api_key = "8323196ca1dfe1aee8ec00e0b885dbae9ab02f3144daf19cd23897c85ba168d2"
				shotgun_link = 'https://rts.shotgunstudio.com'

				sg = Shotgun(shotgun_link, script_name, script_api_key)

				fields = [ 'login' ]
				filters = [ [ 'login', 'is', os.environ.get("USERNAME", None) ] ]
				filters_alt = [ [ 'sg_alt_login', 'contains', os.environ.get("USERNAME", None) ] ]
				humanuser = sg.find_one( "HumanUser", filters, fields )
				humanuser_alt = sg.find_one( "HumanUser", filters_alt, fields )

				# If local user match with shotgun user
				if humanuser:
					return os.environ.get("USERNAME", None)
				# If local user match with shotgun alternative user
				elif humanuser_alt:
					return humanuser_alt['login']

			else:
				return os.environ.get("USERNAMESHOTGUN", None)
		else:
			try:
				import pwd
				pwd_entry = pwd.getpwuid(os.geteuid())
				return pwd_entry[0]
			except:
				return None
		