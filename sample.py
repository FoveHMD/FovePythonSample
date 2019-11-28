# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

import sys
import time

import numpy as np

# You need to include below to your coding for the binding with capi.
import fove
import fove.headset as hs


def main():
    # Name headset capabilities to be used (see `fove.headset`)
    # (For efficiency, capabilities not requested will not be instanciated)
    caps = hs.ClientCapabilities.Gaze + hs.ClientCapabilities.Orientation
    res_caps = hs.ResearchCapabilities.EyeImage

    # Create headset objects etc. in an idimoatic python way.
    # These will be released upon exit from the `with` block.
    with hs.Headset(caps) as headset,\
            headset.createCompositor() as compositor,\
            headset.getResearchHeadset(res_caps) as res_headset:

        # Query some status.
        # Refer to docs for `fove.headset.Headset`, `fove.feadset.ResearchHeadset`
        # and `fove.headset.Compositor` for other APIs.
        print('Headset connected: {}'.format(headset.isHardwareConnected()))
        print('Headset ready: {}'.format(headset.isHardwareReady()))
        print('Versions: {}'.format(headset.getSoftwareVersions()))
        print('Compositor ready: {}'.format(compositor.isReady()))

        # To do anything with the eye tracker, `EyeTracking` hardware has to be ready.
        # If there is something wrong with the creation of `headset` object above,
        # this test may fail.
        #
        # Note that any API request to Fove runtime has a chance to fail (due to I/O errors etc.),
        # which is why they return `Optional[T]` (`None` or a value of `T`).
        # So, to discrimnate API failure with other errors, we have to first check for `None`.
        #
        # For simplicity, however, we do not always check for `None` below.
        ret = headset.isEyeTrackingEnabled()  # -> Option[bool]
        if ret is None:
            print("Failed to communicate with Fove runtime", file=sys.stderr)
            # return 1
        if not ret:
            print("EyeTracking not enabled", file=sys.stderr)
            # return 1

        # Request to start eye tracking calibration if not already calibrated in this session.
        # (See also: `fove.headset.Headset.startEyeTrackingCalibration`)
        ret = headset.ensureEyeTrackingCalibration()
        if not ret:
            print("Eye tracking calibration has failed", file=sys.stderr)
            # return 1

        # At this point either eye tracker has been calibrated, or a request to calibrate has been
        # submitted to the Fove runtime.  Calibration can stil fail and this may return `False`
        ret = headset.isEyeTrackingCalibrated()
        if not ret:
            print("Calibrated: {}".format(ret))
            # return 1

        # There are other queries
        iod = headset.getIOD()
        if iod is not None:
            print("IOD: {}".format(iod.val))

        res_headset.registerCapabilities(res_caps)

        # Capture an eye image (BMP format) into a file
        # Some enum types needed for using `fove.headset.ResearchHeadset` still lives
        # only in `fove.capi`.
        img = res_headset.getImage(fove.capi.ImageType.StereoEye)
        if img is not None:
            arr = np.array(img.image)
            with open("data.bmp", "wb") as fout:
                arr.tofile(fout)

        # Main loop
        t0 = time.time()
        while True:
            # Sync the loop to eye camera frame rate.
            # Should cap the loop at around 120Hz
            # print("t: {:2.4f}".format(time.time() - t0))
            waited = headset.waitForNextEyeFrame()
            if not waited:
                wait_s = 1.0
                print('Failed to sync eye frame; sleeping {}s'.format(wait_s), file=sys.stderr)
                time.sleep(wait_s)
                continue

            # From the `headset` object, can fetch gaze vectors etc. for this frame.
            # These geometrical objects can be converted to appropriate `numpy` arrays
            # when that make sense.
            lGaze, rGaze = headset.getGazeVectors()
            if lGaze is not None:
                lVec = np.array(lGaze.vector)  # 3d vector
                print("Left gaze:  {}".format(lVec))
            if rGaze is not None:
                rVec = np.array(rGaze.vector)
                print("Right gaze: {}".format(rVec))

            matsLH = headset.getProjectionMatricesLH(0.1, 1.0)
            if matsLH is not None:
                lMat, rMat = np.array(matsLH[0]), np.array(
                    matsLH[1])  # 4x4 matrix
                print("Projection Mat(L): {}".format(lMat))

            # Also, there are queries for validity/reliability of the compute data for the current frame
            gazeConv = headset.getGazeConvergence()
            if gazeConv is not None:
                print("Gaze convegence: {}".format(gazeConv))

            eyesClosed = headset.checkEyesClosed()
            if eyesClosed is not None:
                print("Eyes closed:     {}".format(eyesClosed))

            # From the `res_headset` object, can fetch the actual eye image for this frame
            img_ = res_headset.getImage(fove.capi.ImageType.StereoEye)
            if img_ is not None:
                # `fove.headset.BitmapImage` can be constructed from `fove.capi.BitmapImage` (return values of
                # `fove.headset.ResearchHeadset.getImage(type)`):
                img = hs.BitmapImage(img_)
                # `fove.headset.BitmapImage.data` contains a `numpy` array of shape `height x width x channels`
                # so you can for e.g. access the pixels, pass to OpenCV etc.
                # Each element of the `numpy` array is an `np.uint8`.
                #
                # But please note that the images are primarily for Fove researchers and may have preprocessed,
                # have annotations overlayed etc.
                mat = img.data
                # # import cv2 (OpenCV) elsewhere
                # mat = cv2.cvtColor(mat, cv2.COLOR_RGB2BGR)
                # cv2.imshow("eye image", mat)
                # cv2.waitKey(0)
                mat *= 2
                print("First pixel doubled: {},{},{}".format(
                    mat[0][0][0], mat[0][0][1], mat[0][0][2]))


if __name__ == '__main__':
    main()
