##
# @mainpage
#
# This is the documentation for the FOVE Python API, which wraps the FOVE C API
# (also included in this SDK).
#
# This API allows client applications to interface with the FOVE runtime system,
# including headsets, eye tracking, position tracking, and the compositor.
# This package provides a namespace for Python bindings for the the FOVE C API.
#
# Also included is a "Research API", which is intended specifically for researchers
# where the laboratory environment is fully controlled. The research features are
# not inteded for use by games.
#
# The main place to get started is looking at the following classes:
# - \ref fove.headset.Headset
# - \ref fove.headset.ResearchHeadset
# - \ref fove.headset.Compositor
#
# \section install_sec Installation
#
# To use the Python API, configure your `PYTHONPATH` so that the `fove` package
# is visible to the python executable. (SDK distributions >= 0.16.1 contain
# the `fove` package under `<SDK_ROOT>/python/site-packages/fove`.)
#
# Items in the fove.capi namespace provide a very thin wrapper over C API,
# and correspond almost one-to-one to the latter.
#
# Items in the fove.headset add a layer of convenience thereover, and allows
# the user to interact with the runtime using more idiomatic python codes.
#
# Since all functionalities provided by the FOVE C API can be used
# through `fove.headset`, we do not recommend users to use `fove.capi` directly.
#
# \section requirements_sec Requirements
#
# This API requires Python 3.5 or later.
# It may work on earlier versions of Python 3 as well as on Python 2.x,
# but they are not officially supported as of yet.
#
# \section backcompat_sec Backwards Compatibility and API Stability
#
# Since this version of the Fove Python API communicates with the FOVE runtime
# exclusively through the FOVE C API, it provides the same backwards compatibility
# guarantees as the C API does.  In particular, python applications written
# using this version of the Python API should be able to communicate
# with future versions (>= 0.16) of the runtimes, but not with older ones (< 0.16).
# (For more on the compatibility guarantees of the latter, please refer to the section
#  on `Compatibility` in the C API documentation.)
#
# APIs in the `fove.capi` is considered to be as stable as the FOVE C API.
# APIs in the `fove.headset` should be considered experimental and
# might introduce breaking changes in future versions.
