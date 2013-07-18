#!/usr/bin/env python

""" Distutils Setup File for the mx Extensions BASE distribution.

"""
#
# Load configuration(s)
#
import egenix_mx_base
configurations = (egenix_mx_base,)

#
# Run distutils setup...
#
import mxSetup
mxSetup.run_setup(configurations)
