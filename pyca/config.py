# -*- coding: utf-8 -*-
'''
Default configuration for pyCA.
'''

__CFG = '''
[agent]
name             = string(default='pyca')
ignore_timezone  = boolean(default=False)
update_frequency = integer(min=5, default=60)
cal_lookahead    = integer(min=0, default=14)
backup_mode      = boolean(default=false)

[capture]
directory        = string(default='./recordings')
command          = string(default='ffmpeg -nostats -re -f lavfi -r 25 -i testsrc -t {{time}} {{dir}}/{{name}}.mp4')
flavors          = list(default=list('presenter/source'))
files            = list(default=list('{{dir}}/{{name}}.mp4'))
preview_dir      = string(default='./recordings')
preview          = list(default=list())

[server]
url              = string(default='http://mhtest.virtuos.uos.de:8080')
username         = string(default='matterhorn_system_account')
password         = string(default='CHANGE_ME')
insecure         = boolean(default=False)
certificate      = string(default='')

[ui]
username         = string(default='admin')
password         = string(default='opencast')
refresh_rate     = integer(min=1, default=2)
url              = string(default='http://localhost:5000')
'''

cfgspec = __CFG.split('\n')
