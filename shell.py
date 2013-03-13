#!/usr/bin/env python

import IPython
import fsm.config.db
import fsm.config.app as app_config
#import arkplatform2.models_sql as model
from fsm.models import *
import sys
from IPython.frontend.terminal.embed import InteractiveShellEmbed

if __name__ == "__main__":
    print "=== Welcome to SNAC Merge Tool Shell (%s env) ===" % "dev"
    init_model(fsm.config.db.get_db_uri())
    shell = InteractiveShellEmbed()
    shell.user_ns = {}
    shell()
