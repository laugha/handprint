'''
main_body.py: main loop for Handprint

Authors
-------

Michael Hucka <mhucka@caltech.edu> -- Caltech Library

Copyright
---------

Copyright (c) 2018-2019 by the California Institute of Technology.  This code
is open-source software released under a 3-clause BSD license.  Please see the
file "LICENSE" for more information.
'''

import os
from   os import path
import sys
from   sys import exit as exit

import handprint
from handprint.debug import set_debug, log
from handprint.exceptions import *
from handprint.files import filename_extension, files_in_directory, is_url
from handprint.files import readable, writable, filter_by_extensions
from handprint.manager import Manager
from handprint.network import network_available, disable_ssl_cert_check
from handprint.processes import available_cpus
from handprint.services import ACCEPTED_FORMATS, services_list


# Exported classes.
# .............................................................................

class MainBody(object):
    '''Main body for Handprint.'''

    def __init__(self, base_name, extended, from_file, output_dir, threads, say):
        '''Initialize internal state and prepare for running services.'''

        if not network_available():
            raise ServiceFailure('No network.')

        if from_file:
            if not path.exists(from_file):
                raise RuntimeError('File not found: {}'.format(from_file))
            if not readable(from_file):
                raise RuntimeError('File not readable: {}'.format(from_file))

        if output_dir:
            if path.isdir(output_dir):
                if not writable(output_dir):
                    raise RuntimeError('Directory not writable: {}'.format(output_dir))
            else:
                os.mkdir(output_dir)
                if __debug__: log('Created output_dir directory {}', output_dir)

        self._base_name  = base_name
        self._extended   = extended
        self._from_file  = from_file
        self._output_dir = output_dir
        self._threads    = threads
        self._say        = say


    def run(self, services, files):
        '''Run service(s) on files.'''

        # Set shortcut variables for better code readability below.
        base_name  = self._base_name
        extended   = self._extended
        from_file  = self._from_file
        output_dir = self._output_dir
        threads    = self._threads
        say        = self._say

        # Gather up some things and get prepared.
        targets = self.targets_from_arguments(files, from_file)
        if not targets:
            raise RuntimeError('No images to process; quitting.')
        num = len(targets)
        print_separators = num > 1 and not say.be_quiet()
        procs = int(max(1, available_cpus()/2 if threads == 'T' else int(threads)))

        say.info('Will apply services {} to {} image{}.'.format(
            ', '.join(services), num, 's' if num > 1 else ''))
        if self._extended:
            say.info('Will save extended results.')
        say.info('Will use {} process threads.'.format(procs))

        # Get to work.
        if __debug__: log('initializing manager and starting processes')
        manager = Manager(services, procs, output_dir, extended, say)
        for index, item in enumerate(targets, start = 1):
            if print_separators:
                say.msg('='*70, 'dark')
            manager.process(item, index, base_name)
        if print_separators:
            say.msg('='*70, 'dark')


    def targets_from_arguments(self, files, from_file):
        targets = []
        if from_file:
            if __debug__: log('Opening {}', from_file)
            with open(from_file) as f:
                targets = f.readlines()
            targets = [line.rstrip('\n') for line in targets]
            if __debug__: log('Read {} lines from {}.', len(targets), from_file)
        else:
            for item in files:
                if is_url(item):
                    targets.append(item)
                elif path.isfile(item) and filename_extension(item) in ACCEPTED_FORMATS:
                    targets.append(item)
                elif path.isdir(item):
                    # It's a directory, so look for files within.
                    # Ignore files that appear to be the previous output of Handprint.
                    # (These are files that end in, e.g., ".google.jpg")
                    handprint_endings = ['.' + x + '.jpg' for x in services_list()]
                    files = files_in_directory(item, extensions = ACCEPTED_FORMATS)
                    files = filter_by_extensions(files, handprint_endings)
                    targets += files
                else:
                    self._say.warn('"{}" not a file or directory'.format(item))
        return targets