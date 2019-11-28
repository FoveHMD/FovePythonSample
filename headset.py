# @package fove.headset
#
# This module provides a set of higher-level APIs that wraps the FOVE C API.
# Internally, it uses a lower level API in `fove.capi` namespace,
# which we do not document at the moment.
#
# - @ref fove.headset.Headset
# - @ref fove.headset.ResearchHeadset
# - @ref fove.headset.Compositor
#
# @file fove/headset.py
#
# This file implements the `fove.headset` module
#
# Note on Doxygen:
# - remove ../../Python/src/__init_.py when generating docs,
#   otherwise Doxygen would think `src` is a package.
#   (It is, but we do not want to expose it to the doc.)


from __future__ import absolute_import, division, print_function

import logging
import time

import numpy as np

from . import capi

logger = logging.getLogger(__name__)

# Note: This sort of leaks capi types to clients,
# but python2 does not come with class Enum by default
# List of capabilities usable by clients
#
# Most features require registering for the relevant capability.
# If a client queries data related to a capability it has not registered
# capi.ErrorCode.API_NotRegistered will be returned.
#
# This enum is designed to be used as a flag set, so items support arithmetic operations like `+` and `-` as well as the containment operator `in`.
#
# The FOVE runtime will keep any given set of hardware/software running so long as one client is registering a capability.
#
# The registration of a capability does not necessarily mean that the capability is running.
# For example, if no position tracking camera is attached, no position tracking will occur regardless of how many clients registered for it.


class ClientCapabilities(object):
    # No capabilities requested
    None_ = capi.ClientCapabilities.None_  # type: capi.ClientCapabilities
    # Enables eye tracking
    Gaze = capi.ClientCapabilities.Gaze  # type: capi.ClientCapabilities
    # Enables headset orientation tracking
    Orientation = capi.ClientCapabilities.Orientation  # type capi.ClientCapabilities
    # Enables headset position tracking
    Position = capi.ClientCapabilities.Position  # type capi.ClientCapabilities


# Research-API-specific capabilities
class ResearchCapabilities(object):
    None_ = capi.ResearchCapabilities.None_  # type: capi.ResearchCapabilities
    EyeImage = capi.ResearchCapabilities.EyeImage  # type: capi.ResearchCapabilities
    # type capi.ResearchCapabilities
    PositionImage = capi.ResearchCapabilities.PositionImage


# Class that manages accesses to headsets
#
# All Headset-related API requests will be done through an instance of this class.
#
# The class provides `Headset.__enter__` and `Headset.__exit__` methods
# that do relevant resource managements, so the typical use of this class
# would be as follows:
#
# @code
# with Headset(ClientCapabilities.Gaze + ClientCapabilities.Orientation) as headset:
#     # use headset
#     pass
# @endcode
class Headset(object):
    # Defines a headset with the given capabilities
    #
    # This does not automatically create or connect to the headset.
    # For that, the user has to call `Headset.__enter__` (and call `Headset.__exit__`
    # when the headset is no longer needed) but consider using the `with` statement
    # instead of manually calling them.
    #
    # @param capabilities The desired capabilities (Gaze, Orientation, Position).
    # For multiple capabilities, use arithmetic operators as in:
    # `ClientCapabilities.Gaze + ClientCapabilities.Position`.
    # @see Headset.__enter__
    def __init__(self, capabilities):
        # type: (capi.Fove_ClientCapabilities) -> None
        # A Fove_Headset object where the address of the newly created headset will be written upon success
        self._headset = None
        # Capabilities that the user intends to use
        self._caps = capabilities

    # Creates and tries to connect to the headset.
    #
    # The result headset should be destroyed using `Headset.__exit__` when no longer needed,
    # but consider using the `with` statement instead of manually calling it.
    #
    # @return A Headset object where the handle to the newly created headset is written upon success
    # @exception RuntimeError When failed to create a headset
    # @see Headset.__exit__
    def __enter__(self):
        # type: () -> Headset
        logger.debug('Creating headset: {}'.format(self._caps))
        self._headset = capi.Fove_Headset()
        err = capi.createHeadset(self._caps, self._headset)
        if err != capi.ErrorCode.None_:
            raise RuntimeError('Failed to create headset: {}'.format(err))
        return self

    # Frees resources used by a headset object, including memory and sockets
    #
    # Upon return, this headset instance, and any research headsets from it, should no longer be used.
    # @see Headset.__enter__
    def __exit__(self, _e_type, _e_val, _traceback):
        # no type: (Optional[Type[BaseException]], Optional[Type[BaseException]], Optional[TracebackType]) -> bool
        if _e_type is not None:
            logger.error('Headset: exception raised: {}'.format(_e_val))
        if self._headset is not None:
            capi.Headset_destroy(self._headset)
            logger.debug('Destroyed headset')
        return True if _e_type is None else False

    # Checks whether the headset is connected or not.
    #
    # @return True if an HMD is known to be connected, False otherwise (including the case
    # when any error detected that might make the query result unreliable).
    # @see Headset.createHeadset
    def isHardwareConnected(self):
        # type: () -> bool
        b = capi.Bool(False)
        err = capi.Headset_isHardwareConnected(self._headset, b)
        if err != capi.ErrorCode.None_ or not b.val:
            logger.error('Failed to get hardware connectivity: {}'.format(err))
            return False
        return True

    # Checks whether the headset hardware has started.
    #
    # @return True if the hardware for the requested capabilities has started, False otherwise
    # (including the case when any error detected that might make the query result unreliable)
    def isHardwareReady(self):
        # type: () -> bool
        b = capi.Bool(False)
        err = capi.Headset_isHardwareReady(self._headset, b)
        if err != capi.ErrorCode.None_ or not b.val:
            logger.error('Failed to get hardware readiness: {}'.format(err))
            return False
        return True

    # XXX return value bool instead of throwing
    # Checks whether the client can run against the installed version of the FOVE SDK.
    #
    # @return capi.ErrorCode.None_ if this client is compatible with the currently running service
    # @exception RuntimeError if not compatible with the currently running service
    def checkSoftwareVersions(self):
        # type: () -> capi.Fove_ErrorCode
        err = capi.Headset_checkSoftwareVersions(self._headset)
        if err != capi.ErrorCode.None_:
            # err should be ErrorCode.Connect_RuntimeVersionTooOld
            raise RuntimeError('Incompatible SDK version: {}'.format(err))
        return err

    # Gets the information about the current software versions.
    #
    # Allows you to get detailed information about the client and runtime versions.
    # Instead of comparing software versions directly, you should simply call
    # `Headset.checkSoftwareVersions` to ensure that the client and runtime are compatible.
    #
    # @return information about the current software versions, or None in case of API failure.
    def getSoftwareVersions(self):
        # type: () -> Optional[capi.Versions]
        versions = capi.Versions()
        err = capi.Headset_getSoftwareVersions(self._headset, versions)
        if err != capi.ErrorCode.None_:
            logger.error('Failed to get software versions: {}'.format(err))
            return None
        return versions

    # Gets the information about the hardware information
    #
    # Allows you to get serial number, manufacturer, and model name of the headset.
    #
    # @return information about the hardware, or None in case of API failure.
    def getHardwareInfo(self):
        # type: () -> Optional[capi.HardwareInfo]
        hardwareInfo = capi.HardwareInfo()
        err = capi.Headset_getSoftwareVersions(self._headset, hardwareInfo)
        if err != capi.ErrorCode.None_:
            logger.error('Failed to get hardware information: {}'.format(err))
            return None
        return hardwareInfo

    # Waits for next camera frame and associated eye tracking info becomes available.
    #
    # Allows you to sync your eye tracking loop to the actual eye-camera loop.
    # On each loop, you would first call this blocking function to wait for a new frame
    # and then proceed to consume eye tracking info accociated with the frame.
    #
    # @return (bool, Optional[bool])
    # @return The first return value is True if it successfully synced with the camera
    # frames; otherwise it is False.
    # @return When the first return value is False, the second return value indicates
    # whether the error is permanent: i.e. it is False when the call to an internal
    # API has just timed out and retry on the client side might be useful;
    # it is otherwise True, e.g. if the Gaze capability was not registered.
    def waitForNextEyeFrame(self):
        # type: () -> Tuple[bool, Optional[bool]]
        err = capi.Headset_waitForNextEyeFrame(self._headset)
        if err == capi.ErrorCode.None_:
            return True, None
        elif err == capi.ErrorCode.API_Timeout:
            return False, False  # client may retry
        else:
            return False, True

    # Gets each eye's current gaze vector
    #
    # Note: the underlying API in fove.capi allows one to get only one of
    # the two (left/right) gaze vectors, but here both vectors
    # will always be returned.
    #
    # @return (Optional[capi.GazeVector], Optional[capi.GazeVector])
    # @return left eye gaze vector, or None in case of API failure
    # @return right eye gaze vector, or None in case of API failure
    def getGazeVectors(self):
        # type: () -> Tuple[Optional[capi.GazeVector], Optional[capi.GazeVector]]
        lGaze, rGaze = capi.GazeVector(), capi.GazeVector()
        err = capi.Headset_getGazeVectors(self._headset, lGaze, rGaze)
        if err != capi.ErrorCode.None_:
            logger.error('Failed to get current gaze vectors: {}'.format(err))
            return None, None
        return lGaze, rGaze

    # Gets the user's 2D gaze position on the screens seen through the HMD's lenses
    #
    # The use of lenses and distortion correction creates a screen in front of each eye.
    # This function returns 2D vectors representing where on each eye's screen the user
    # is looking.
    #
    # The vectors are normalized in the range [-1, 1] along both X and Y axes such that the
    # following points are true:
    #
    # - Center: (0, 0)
    # - Bottom-Left: (-1, -1)
    # - Top-Right: (1, 1)
    #
    # @return (Optional[capi.Vec2], Optional[capi.Vec2])
    # @return left eye gaze point in the HMD's virtual screen space
    # @return right eye gaze point in the HMD's virtual screen space
    def getGazeVectors2d(self):
        # type: () -> Tuple[Optional[capi.Vec2], Optional[capi.Vec2]]
        lGaze, rGaze = capi.Vec2(), capi.Vec2()
        err = capi.Headset_getGazeVectors2D(self._headset, lGaze, rGaze)
        if err != capi.ErrorCode.None_:
            logger.error(
                'Failed to get current 2d gaze vectors: {}'.format(err))
            return None, None
        return lGaze, rGaze

    # Gets eye convergence data
    #
    # @return the convergence data, or None in case of API failure
    def getGazeConvergence(self):
        # type: () -> Optional[capi.GazeConvergenceData]
        conv = capi.GazeConvergenceData()
        err = capi.Headset_getGazeConvergence(self._headset, conv)
        if err != capi.ErrorCode.None_:
            logger.error('Failed to get gaze convergence data: {}'.format(err))
            return None
        return conv

    # Returns eyes that are closed
    #
    # @return eyes that are closed encoded as capi.Eye, or None in case of API failure
    def checkEyesClosed(self):
        # type: () -> Optional[capi.Eye]
        eyes = capi.Eye.Both
        err = capi.Headset_checkEyesClosed(self._headset, eyes)
        if err != capi.ErrorCode.None_:
            logger.error('Failed to get eyes that are closed: {}'.format(err))
            return None
        return eyes

    # Returns eyes that are being tracked
    #
    # @return eyes that are being tracked encoded as capi.Eye, or None in case of API failure
    def checkEyesTracked(self):
        # type: () -> Optional[capi.Eye]
        eyes = capi.Eye.Both
        err = capi.Headset_checkEyesTracked(self._headset, eyes)
        if err != capi.ErrorCode.None_:
            logger.error('Failed to get eyes being tracked: {}'.format(err))
            return None
        return eyes

    # Checks if eye tracking hardware has started
    #
    # @return whether eye tracking hardware has started, or None in case of API failure
    def isEyeTrackingEnabled(self):
        # type: () -> Optional[bool]
        b = capi.Bool(False)
        err = capi.Headset_isEyeTrackingEnabled(self._headset, b)
        if err != capi.ErrorCode.None_:
            logger.error(
                'Failed to check if eye tracking hardware has started: {}'.
                format(err))
            return None
        return b.val

    # Checks if eye tracking has been calibrated
    #
    # @return whether eye tracking hardware has been calibrated, or None in case of API failure
    def isEyeTrackingCalibrated(self):
        # type: () -> Optional[bool]
        b = capi.Bool(False)
        err = capi.Headset_isEyeTrackingCalibrated(self._headset, b)
        if err != capi.ErrorCode.None_:
            logger.error(
                'headset.isEyeTrackingCalibrated() failed: {}'.format(err))
            return None
        return b.val

    # Checks if eye tracking is in the process of calibration
    #
    # @return whether eye tracking is in the process of calibration, or None in case of API failure
    def isEyeTrackingCalibrating(self):
        # type: () -> Optional[bool]
        b = capi.Bool(False)
        err = capi.Headset_isEyeTrackingCalibrating(self._headset, b)
        if err != capi.ErrorCode.None_:
            logger.error(
                'headset.isEyeTrackingCalibrating() failed: {}'.format(err))
            return None
        return b.val

    # Checks if eye tracking is actively tracking an eye - or eyes.
    #
    # @return whether eye tracking is active, or None in case of API failure
    def isEyeTrackingReady(self):
        # type: () -> Optional[bool]
        b = capi.Bool(False)
        err = capi.Headset_isEyeTrackingReady(self._headset, b)
        if err != capi.ErrorCode.None_:
            logger.error('headset.isEyeTrackingReady() failed: {}'.format(err))
            return None
        return b.val

    # Checks if motion tracking hardware has started
    #
    # @return whether motion tracking hardware has started, or None in case of API failure
    def isMotionReady(self):
        # type: () -> Optional[bool]
        b = capi.Bool(False)
        err = capi.Headset_isMotionReady(self._headset, b)
        if err != capi.ErrorCode.None_:
            logger.error('headset.isMotionReady() failed: {}'.format(err))
            return None
        return b.val

    # XXX api - what would users want in case of failure
    # Tares the orientation of the headset
    #
    # @return None
    def tareOrientationSensor(self):
        # type: () -> None
        err = capi.Headset_tareOrientationSensor(self._headset)
        if err != capi.ErrorCode.None_:
            logger.error(
                'headset.tareOrientationSensor() failed: {}'.format(err))

    # Checks if position tracking hardware has started
    #
    # @return whether position tracking hardware has started, or None in cased of API failure

    def isPositionReady(self):
        # type: () -> Optional[bool]
        b = capi.Bool(False)
        err = capi.Headset_isPositionReady(self._headset, b)
        if err != capi.ErrorCode.None_:
            logger.error('headset.isPositionReady() failed: {}'.format(err))
            return None
        return b.val

    # XXX api - what would users want in case of failure
    # Tares the position of the headset
    #
    # @return None
    def tarePositionSensors(self):
        # type: () -> None
        err = capi.Headset_tarePositionSensors(self._headset)
        if err != capi.ErrorCode.None_:
            logger.error(
                'headset.tarePositionSensors() failed: {}'.format(err))

    # Gets the pose of the head-mounted display
    #
    # @return Current pose of the head-mounted display, or None in case of API failure
    def getLatestPose(self):
        # type: () -> Optional[capi.Pose]
        pose = capi.Pose()
        err = capi.Headset_getLatestPose(self._headset, pose)
        if err != capi.ErrorCode.None_:
            logger.error('headset.getLatestPose() failed: {}'.format(err))
            return None
        return pose

    # Gets the valoues of passed-in left-handed 4x4 projection matrices
    #
    # Gets 4x4 projection matrices for both eyes using near and far planes
    # in a left-handed coordinate system.
    #
    # Note: the underlying API in fove.capi allows one to get only one of
    # the two (left/right) projection matrices, but here both matrices
    # will always be returned.
    #
    # @param zNear        The near plane in float, Range: from 0 to zFar
    # @param zFar         The far plane in float, Range: from zNear to infinity
    # @return (Optional[capi.Matrix44], Optional[capi.Matrix44])
    # @return left 4x4 projection matrix (left-handed), or None in case of API failure
    # @return right 4x4 projection matrix (left-handed), or None in case of APi failure
    def getProjectionMatricesLH(self, zNear, zFar):
        # type: (float, float) -> Tuple[Optional[capi.Matrix44], Optional[capi.Matrix44]]
        lMat, rMat = capi.Matrix44(), capi.Matrix44()
        err = capi.Headset_getProjectionMatricesLH(self._headset, zNear, zFar,
                                                   lMat, rMat)
        if err != capi.ErrorCode.None_:
            logger.error(
                'headset.getProjectionMatricesLH() failed: {}'.format(err))
            return None, None
        return lMat, rMat

    # Gets the valoues of passed-in right-handed 4x4 projection matrices
    #
    # Gets 4x4 projection matrices for both eyes using near and far planes
    # in a right-handed coordinate system.
    #
    # Note: the underlying API in fove.capi allows one to get only one of
    # the two (left/right) projection matrices, but here both matrices
    # will always be returned.
    #
    # @param zNear        The near plane in float, Range: from 0 to zFar
    # @param zFar         The far plane in float, Range: from zNear to infinity
    # @return (Optional[capi.Matrix44], Optional[capi.Matrix44])
    # @return left 4x4 projection matrix (left-handed), or None in case of API failure
    # @return right 4x4 projection matrix (left-handed), or None in case of API failure
    def getProjectionMatricesRH(self, zNear, zFar):
        # type: (float, float) -> Tuple[Optional[capi.Matrix44], Optional[capi.Matrix44]]
        lMat, rMat = capi.Matrix44(), capi.Matrix44()
        err = capi.Headset_getProjectionMatricesRH(self._headset, zNear, zFar,
                                                   lMat, rMat)
        if err != capi.ErrorCode.None_:
            logger.error(
                'headset.getProjectionMatricesRH() failed: {}'.format(err))
            return None, None
        return lMat, rMat

    # Gets values for the view frustum of both eyes at 1 unit away
    #
    # Gets values for the view frustum of the specified eye at 1 unit away. Please multiply them by zNear to
    # convert to your correct frustum near-plane. Either outLeft or outRight may be `nullptr` to only write the
    # other struct, however setting both to `nullptr` is considered and error and the function will return
    # `Fove_ErrorCode::API_NullOutPointersOnly`.
    #
    # @return (Optional[capi.ProjectionParams],Optional[capi.ProjectionParams])
    # @return the struct describing the left camera projection parameters, or None in case of API failure
    # @return the struct describing the right camera projection parameters, or None in case of API failure
    def getRawProjectionValues(self):
        # type: () -> Tuple[Optional[capi.ProjectionParams],Optional[capi.ProjectionParams]]
        lParams, rParams = capi.ProjectionParams(), capi.ProjectionParams()
        err = capi.Headset_getRawProjectionValues(self._headset, lParams,
                                                  rParams)
        if err != capi.ErrorCode.None_:
            logger.error(
                'headset.getRawProjectionValues() failed: {}'.format(err))
            return None, None
        return lParams, rParams

    # Gets the matrices to convert from eye- to head-space coordintes.
    #
    # This is simply a translation matrix that returns +/- IOD/2
    #
    # @return (Optional[capi.Matrix44], Optional[capi.Matrix44])
    # @return the matrix describing left-eye transform data, or None in case of API failure
    # @return the matrix describing right-eye transform data, or None in case of API failure
    def getEyeToHeadMatrices(self):
        # type: () -> Tuple[Optional[capi.Matrix44], Optional[capi.Matrix44]]
        lMat, rMat = capi.Matrix44(), capi.Matrix44()
        err = capi.Headset_getEyeToHeadMatrices(self._headset, lMat, rMat)
        if err != capi.ErrorCode.None_:
            logger.error(
                'headset.getEyeToHeadMatrices() failed: {}'.format(err))
            return None, None
        return (lMat, rMat)

   # Gets interocular distance in meters
   #
   # This is an estimation of the distance between centers of the left and right eyeballs.
   # Half of the IOD can be used to displace the left and right cameras for stereoscopic rendering.
   # We recommend calling this each frame when doing stereoscoping rendering.
   # Future versions of the FOVE service may update the IOD during runtime as needed.
   #
   # @return A floating point value describing the IOD, or None in case of API failure
    def getIOD(self):
        # type: () -> Optional[float]
        iod = capi.Float(-1.0)
        err = capi.Headset_getIOD(self._headset, iod)
        if err != capi.ErrorCode.None_:
            logger.error('headset.getIOD() failed: {}'.format(err))
            return None
        return iod

    # Starts eye tracking calibration if not already calibrated
    #
    # Does nothing if the user is already calibrated.
    # Does nothing if the calibration is currently running.
    # All eye tracking content should call this before using the gaze to ensure that there's a valid calibration.
    # After calling this, content should periodically poll for
    # Headset.isEyeTrackingCalibrating to become false,
    # so as to ensure that the content is not updating while obscured by the calibrator
    #
    # @return True if the request has been successfully made, None otherwise.
    def ensureEyeTrackingCalibration(self):
        # type: () -> Optional[Bool]
        err = capi.Headset_ensureEyeTrackingCalibration(self._headset)
        if err != capi.ErrorCode.None_:
            logger.error(
                'headset.ensureEyeTrackingCalibration() failed: {}'.format(
                    err))
            return None
        return True

    # Starts eye tracking calibration
    #
    # @param restartIfRunning If True, this will cause the calibration to restart if it's already running.
    # Otherwise this will do nothing if eye tracking calibration is currently running.
    # @return True if the request has been successfully made, None otherwise.
    def startEyeTrackingCalibration(self, restartIfRunning):
        # type: () -> Optional[Bool]
        err = capi.Headset_startEyeTrackingCalibration(self._headset,
                                                       restartIfRunning)
        if err != capi.ErrorCode.None_:
            logger.error(
                'headset.startEyeTrackingCalibration() failed: {}'.format(err))
            return None
        return True

    # Stops eye tracking calibration
    #
    # @return True if the request has been successfully made, None otherwise.
    def stopEyeTrackingCalibration(self):
        # type: () -> None
        err = capi.Headset_stopEyeTrackingCalibration(self._headset)
        if err != capi.ErrorCode.None_:
            logger.error(
                'headset.stopEyeTrackingCalibration() failed: {}'.format(err))
            return None
        return True

    # Returns a compositor interface from the given headset
    #
    # Each call to this function creates a new object.
    # Once Compositor.__enter__ is called on the object, it should be destroyed with Compositor.__exit__.
    #
    # It is fine to call this function multiple times with the same headset.
    # It is ok for the compositor to outlive the headset passed in.
    #
    # @see Compositor
    # @see Compositor.__enter__
    # @see Compositor.__exit__
    def createCompositor(self):
        # type: () -> Compositor
        return Compositor(self._headset)

    # Converts an existing headset object into a research headset
    #
    # The research API does not provide backwards or forwards compatibility with different FOVE runtimes.
    # Do not release general purpose software using this API, this is meant for researcher user in a controlled environment (lab).
    # The result ResearchHeadset is destroyed when the input headset object is destroyed. There is no destroy/free function for the research headset specifically.
    #
    # @param caps These capabilities are automatically passed to ResearchHeadset_registerCapabilities so as to avoid an extra call
    # @param outHeadset A pointer where the address of the newly created research headset object will be written upon success
    def getResearchHeadset(self, capabilities):
        # type: (capi.ClientCapabilities) -> ResearchHeadset
        return ResearchHeadset(self._headset, capabilities)


# Class that manages accesses to the compositor
#
# All Compositor-related API requests will be done through an instance of this class.
#
# The class provides `Compositor.__enter__` and `Compositor.__exit__` methods
# that do relevant resource managements, and the `Headset` instance has
# a factory method that creates a compositor.
#
# It is fine to create multiple compositors from the same headset.
# It is also fine for the compositor to outlive the headset passed in.
#
# A typical use of this class
# would be as follows:
#
# @code
# with Headset(ClientCapabilities.Gaze) as headset,
#      headset.createCompositor() as compositor:
#     # use compositor
#     pass
# @endcode
class Compositor(object):
    # Defines a compositor that can be created from a headset
    #
    # Normally, this method is invoked through Headset.createCompositor.
    # But unlike in the C API, the user has to call Compositor.__enter__
    # on the result of Compositor.__init__ or Headset.createCompositor
    # to actually connect to a compositor.
    #
    # @param headset An instance of capi.Headset from which this compositor will be created.
    # (Note that it is not an instance of the Headset class defined in this module.)
    # @see Headset.createCompositor
    # @see Compositor.__enter__
    def __init__(self, headset):
        # type: (capi.Fove_Headset) -> None
        self._headset = headset  # XXX this is perhaps ugly, but we cannot pass args to __enter__
        self._compositor = None

    # Creates a compositor interface to the given headset
    #
    # Each call to this function creates and stores a new compositor object,
    # which should be destroyed by calling Compositor.__exit__ on self,
    # which is also retuned from this function.
    #
    # @return self with a reference to a compositor object
    #
    # @see Headset.createCompositor
    # @see Compositor.__exit__
    def __enter__(self):
        # type: () -> Compositor
        logger.debug('Creating compositor: headset: {}'.format(self._headset))
        self._compositor = capi.Fove_Compositor()
        err = capi.Headset_createCompositor(self._headset, self._compositor)
        if err != capi.ErrorCode.None_:
            raise RuntimeError('Failed to create compositor: {}'.format(err))
        # XXX None clear self._headset here?
        return self

    # Frees resources used by the compositor object, including memory and sockets
    #
    # Upon return, this instance for the compositor should no longer be used.
    # @see Compositor.__enter__
    # @see Headset.createCompositor
    def __exit__(self, _e_type, _e_val, _traceback):
        # no type: (Optional[Type[BaseException]], Optional[Type[BaseException]], Optional[TracebackType]) -> bool
        if _e_type is not None:
            logger.error('Headset: exception raised: {}'.format(_e_val))
        if self._compositor is not None:
            capi.Compositor_destroy(self._compositor)
            logger.debug('Destroyed compositor')
        return True if _e_type is None else False

    # Create a layer for this client
    #
    # This function creates a layer upon which frames may be submitted to the compositor by this client.
    #
    # A connection to the compositor must exist for this to pass.
    # This means you need to wait for Compositor.isReady before calling this function.
    # However, if connection to the compositor is lost and regained, this layer will persist.
    # For this reason, you should not recreate your layers upon reconnection, simply create them once.
    #
    # There is no way to delete a layer once created, other than to destroy the Compositor object.
    # This is a feature we would like to add in the future.
    #
    # @param layerInfo The settings for the layer to be created
    # @return A struct that holds the defaults of the newly created layer
    #
    # @see Compositor.isReady
    # @see Compositor.submit
    def createLayer(self, layerInfo):
        # type: (capi.CompositorLayerCreateInfo) -> Optional[capi.CompositorLayer]
        layer = capi.CompositorLayer()
        err = capi.Compositor_createLayer(self._compositor, layerInfo, layer)
        if err != capi.ErrorCode.None_:
            logger.error('compositor.createLayer() failed: {}'.format(err))
            return None
        return layer

    # Submit a frame to the compositor
    #
    # This function takes the feed from your game engine to the compositor for output.
    # @param submitInfo   An array of layerCount capi.CompositorLayerSubmitInfo structs, each of which provides texture data for a unique layer
    # @param layerCount   The number of layers you are submitting
    # @return True if successfully submitted, or None in case of API failure
    def submit(self, submitInfo, layerCount):
        # type: (capi.CompositorLayerSubmitInfo, int) -> Bool
        err = capi.Compositor_submit(self._compositor, submitInfo, layerCount)
        if err != capi.ErrorCode.None_:
            logger.error('compositor.submit() failed: {}'.format(err))
            return None
        return True

    # Wait for the most recent pose for rendering purposes
    #
    # All compositor clients should use this function as the sole means of limiting their frame rate.
    # This allows the client to render at the correct frame rate for the HMD display.
    # Upon this function returning, the client should proceed directly to rendering,
    # to reduce the chance of missing the frame.
    # This function will return the latest pose (valid if not None) as a conveience to the caller.
    #
    # In general, a client's main loop should look like:
    # @code
    # # with compositor
    # while True:
    #    Update()                                   # Run AI, physics, etc, for the next frame
    #    pose, err = compositor.waitForRenderPose() # Wait for the next frame, and get the pose
    #    if pose:
    #        Draw(pose)                             # Render the scene using the new pose
    #    elif err is False:
    #        # sleep a bit and retry
    #        continue
    #    else:
    #        # permanent error
    #        break
    # @endcode
    #
    # @return (Optional[capi.Pose], Optional[bool])
    # @return The first return value is the current pose if the call synced with
    # the compositor frames; otherwise it is None.
    # @return When the first return value is None, the second return value indicates
    # whether the error is permanent: i.e. it is False when the call to an internal
    # API has just timed out and retry on the client side might be useful;
    # it is otherwise True, e.g. if the Orientation capability was not registered.
    def waitForRenderPose(self):
        # type: () -> Tuple[Optional[capi.Pose], Optional[bool]]
        pose = capi.Pose()
        err = capi.Compositor_waitForRenderPose(self._compositor, pose)
        if err == capi.ErrCode.None_:
            return pose, None
        elif err == capi.ErrCode.API_Timeout:
            return None, False  # client may retry
        else:
            return None, True

    # Gets the last cached pose for rendering purposes, without waiting for a new frame to arrive.
    #
    # @return Last cached pose, or None in case of API failure
    def getLastRenderPose(self):
        # type: () -> Optional[capi.Pose]
        pose = capi.Pose()
        err = capi.Compositor_getLastRenderPose(self._compositor, pose)
        if err != capi.ErrorCode.None_:
            logger.error(
                'compositor.getLastRenderPose() failed: {}'.format(err))
            return None
        return pose

    # Checks whether we are connected to a running compositor and ready to submit frames for composing
    #
    # @return True if we are connected to a running compositor and ready to submit frames for compositing, False if not,
    # or else None in case of API failure
    def isReady(self):
        # type: () -> Optional[bool]
        b = capi.Bool(False)
        err = capi.Compositor_isReady(self._compositor, b)
        if err != capi.ErrorCode.None_:
            logger.error('compositor.isReady() failed: {}'.format(err))
            return None
        return b.val

    # Returns the ID of the GPU currently attached to the headset
    #
    # For systems with multiple GPUs, submitted textures to the compositor must
    # come from the same GPU that the compositor is using.
    #
    # @return The adapter ID, or None in case of API failure
    def getAdapterId(self):
        # type: () -> Optional[capi.AdapterId]
        adapterId = capi.AdapterId()
        err = capi.Compositor_getAdapterId(self._compositor, adapterId)
        if err != capi.ErrorCode.None_:
            logger.error('compositor.getAdapterId() failed: {}'.format(err))
            return None
        return adapterId


# Class that manages accesses to the ResearchHeadset
#
# All ResearchHeadset-related API requests will be done through an instance of this class.
#
# The ResearchHeadset is destroyed when the input Headset object is destroyed.
# (It is users' responsibility to ensure that no API functionalities will be used
# through the ResearchHeadset handler, once the underlying Headset is destroyed.)
#
# There is no destroy/free function for the research headset specifically.
# But the class still provides `ResearchHeadset.__enter__` and `ResearchHeadset.__exit__` methods,
# and the `Headset` instance has a factory method that creates a ResearchHeadset.
#
# A typical use of this class would be as follows:
#
# @code
# with Headset(ClientCapabilities.Gaze) as headset,
#      headset.getResearchHeadset(ResearchCapabilities.EyeImage) as research_headset:
#     # use research_headset
#     pass
# @endcode
class ResearchHeadset(object):
    # Gets a ResearchHeadset that can be created from a headset
    #
    # Normally, this method is invoked through Headset.getResearchHeadset.
    #
    # @param headset An instance of capi.Headset from which this compositor will be created.
    # (Note that it is not an instance of the Headset class defined in this module.)
    # @param capabilities Research capabilities
    # @see Headset.getResearchHeadset
    # @see ResearchHeadset.__enter__
    def __init__(self, headset, capabilities):
        # type: (capi.Fove_Headset, capi.ResearchCapabilities) -> None
        self._headset = headset
        self._caps = capabilities
        self._research_headset = None

    # Converts an existing headset object into a research headset.
    #
    #
    def __enter__(self):
        # type: () -> ResearchHeadset
        logger.debug('Creating research headset: headset: {}'.format(
            self._headset))
        self._research_headset = capi.Fove_ResearchHeadset()
        err = capi.Headset_getResearchHeadset(self._headset, self._caps,
                                              self._research_headset)
        if err != capi.ErrorCode.None_:
            raise RuntimeError(
                'Failed to create research headset: {}'.format(err))
        return self

    # Destroyes the headset
    #
    # (no cleanup needed)
    def __exit__(self, _e_type, _e_val, _traceback):
        # no type: (Optional[Type[BaseException]], Optional[Type[BaseException]], Optional[TracebackType]) -> bool
        # not cleanup needed for ourselves
        if _e_type is not None:
            logger.error('Headset: exception raised: {}'.format(_e_val))
            return False
        return True

    # Registers a research capability, enabling the required hardware as needed
    #
    # Normally this is invoked directly via Headset.getResearchHeadset.
    # You can add and remove capabilities while the object is alive.
    #
    # @param caps A set of capabitilties to register. Reregistering an existing capability is a no-op
    def registerCapabilities(self, capabilities):
        # type: (capi.ResearchCapabilities) -> Optional[bool]
        err = capi.ResearchHeadset_registerCapabilities(
            self._research_headset, capabilities)
        if err != capi.ErrorCode.None_:
            logger.error(
                'research_headset.registerCapabilities() failed: {}'.format(
                    err))
            return None
        return True

    # Deregisters a research capability previously registed with registerResearchCapabilities
    #
    # @param caps A set of capabitilties to unregister.
    # Unregistering a non-existing capability is a no-op
    def unregisterCapabilities(self, capabilities):
        # type: (capi.ResearchCapabilities) -> Optional[bool]
        err = capi.ResearchHeadset_unregisterCapabilities(
            self._research_headset, capabilities)
        if err != capi.ErrorCode.None_:
            logger.error(
                'research_headset.unregisterCapabilities() failed: {}'.format(
                    err))
            return None
        return True

    # Returns the latest image of the given type
    #
    # The image data buffer is invalidated upon the next call to this function with the same image type
    #
    # @param imageType type of image to be obtained [capi.ImageType]
    def getImage(self, imageType):
        # type: (capi.ImageType) -> Optional[capi.BitmapImage]
        img = capi.BitmapImage()
        err = capi.ResearchHeadset_getImage(self._research_headset, imageType,
                                            img)
        if err != capi.ErrorCode.None_:
            logger.error('research_headset.getImage() failed: {}'.format(err))
            return None
        return img

    # Returns research-related information from eye tracking.
    def getGaze(self):
        # type: () -> Optional[capi.ResearchGaze]
        gaze = capi.ResearchGaze()
        err = capi.ResearchHeadset_getGaze(self._research_headset, gaze)
        if err != capi.ErrorCode.None_:
            logger.error('research_headset.getGaze() failed: {}'.format(err))
            return None
        return gaze


def parseBmpHeader(image):
    # type: np.array -> (np.uint32, np.uint32, np.uint32, np.uint32, np.uint32, bool)
    # BMP header:
    #  0 ..  2: magic:           char[2] ("BM", could be "BA" etc on OS/2)
    #  2 ..  6: bmp size:        uint32
    #  6 .. 10: reserved
    # 10 .. 14: data offset:     uint32  (offset where pixel array starts)
    # DIB header:
    # 14 .. 18: DIB header size: uint32
    # 18 .. 22: image width:     uint16
    # 22 .. 26: image height:    uint16
    # 26 .. 28: image plane:     uint16
    # 28 .. 30: bits per pixel:  uint16
    if len(image) < 30:
        raise Exception("Invalid BMP image")
    magic = image[:2]
    # 'B', 'M' (only support Win BMP format as that is what Fove0 camera gives)
    if magic[0] != 66 or magic[1] != 77:
        raise Exception("Malformed or unsupported BMP image header")
    size = np.frombuffer(image, dtype=np.uint32, offset=2, count=1)[0]
    data_offset = np.frombuffer(image, dtype=np.uint32, offset=10, count=1)[0]
    # BMPs are scanned by default from the bottom to the top (i.e. "flipped")
    # in which case the height in the header is positive.
    # Negative heights in the header implies that the BMP is scanned from the
    # top to the bottom ("unflipped")
    width = np.frombuffer(image, dtype=np.uint32, offset=18, count=1)[0]
    height = np.frombuffer(image, dtype=np.int32, offset=22, count=1)[0]
    flipped = True if height > 0 else False
    height = height if flipped else -height
    bits_per_pixel = np.frombuffer(
        image, dtype=np.uint16, offset=28, count=1)[0]
    channels = bits_per_pixel // 8
    return (size, width, height, channels, data_offset, flipped)


class BitmapImage(object):
    def __init__(self, img):
        # type: (capi.BitmapImage) -> None
        self.timestamp = img.timestamp
        self.type = img.type
        self.image = np.frombuffer(img.image, dtype=np.uint8)
        size, width, height, channels, data_offset, flipped = parseBmpHeader(
            self.image)
        self.width, self.height, self.channels = width, height, channels
        self.flipped = flipped
        self.data = np.frombuffer(
            self.image,
            dtype=np.uint8,
            offset=data_offset,
            count=height * width * channels,
        ).reshape(height, width, channels)
