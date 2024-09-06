# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

import sys
import time
import numpy as np
import keyboard

# You need to include below to your coding for the binding with capi.
from fove import capi
import fove.headset as hs

# This can help to convert bmp binary data into numpy image
import bitmap


def main():
    # Name headset capabilities to be used (see `fove.headset`)
    # (For efficiency, capabilities not requested will not be instanciated)
    caps = (
        capi.ClientCapabilities.None_
        + capi.ClientCapabilities.EyeTracking
        + capi.ClientCapabilities.OrientationTracking
        + capi.ClientCapabilities.EyesImage
    )

    # Create headset objects etc. in an idimoatic python way.
    # These will be released upon exit from the `with` block.
    with hs.Headset(caps) as headset, headset.createCompositor() as compositor:
        # Query some status.
        # Refer to docs for `fove.headset.Headset`, `fove.feadset.ResearchHeadset`
        # and `fove.headset.Compositor` for other APIs.
        while not headset.isHardwareConnected().value:
            print("Headset not connected, waiting...")
            time.sleep(1)
        print(f"Headset connected: {headset.isHardwareConnected().value}")
       
        version = headset.querySoftwareVersions().value
        print(f"Version: {version.clientMajor}.{version.clientMinor}.{version.clientBuild}")
        print(f"Runtime: {version.runtimeMajor}.{version.runtimeMinor}.{version.runtimeBuild}")
        
        while not compositor.isReady():
            print("Compositor not ready, waiting...")
            time.sleep(1)
        print(f"Compositor ready: {compositor.isReady()}")
        
        ### Main loop
        while True:
            # Press space to start calibration, calibration goes asynchronously
            if keyboard.is_pressed("space"):
                    ret = headset.startEyeTrackingCalibration(options=None)
                    if not ret.isValid():
                        print("Failed to start eye tracking calibration", file=sys.stderr)

            # Sync the loop to eye camera frame rate.
            # Should cap the loop at around 120Hz for FOVE0
            # print(f"t: {(time.time() - t0):2.4f}")
            waited = headset.waitForProcessedEyeFrame()
            if not waited.isValid() or not waited.succeeded:
                wait_s = 1.0
                print(
                    f"Failed to sync eye frame: {waited.error}, sleeping {wait_s}s",
                    file=sys.stderr,
                )
                time.sleep(wait_s)
                continue

            # Need to explicitly fetch the eye tracking data to get an update
            timestamp = headset.fetchEyeTrackingData()
            if not timestamp.isValid():
                print(f"Failed to fetch eye tracking data: {timestamp.error}")
                # return 1

            # Also, there are queries for validity/reliability of the compute
            # data for the current frame
            gazeComb = headset.getCombinedGazeRay()
            if gazeComb.isValid():
                print(f"Gaze convegence: {np.array(gazeComb.value.direction)}")

            eyeStateL = headset.getEyeState(capi.Eye.Left)
            eyeStateR = headset.getEyeState(capi.Eye.Right)
            if eyeStateL.isValid() and eyeStateR.isValid():
                if eyeStateL.value == capi.EyeState.Closed:
                    print("Left eye is closed")
                if eyeStateR.value == capi.EyeState.Closed:
                    print("Right eye is closed")
            else:
                print(f"Failed to fetch L or R eye state, or both: {eyeStateL.error}/{eyeStateR.error}")

            # Again, need to explicitly fetch the eye tracking data to get an update
            timestamp = headset.fetchEyesImage()
            if not timestamp.isValid():
                print(f"Failed to fetch eye image data: {timestamp.error}")
            img = headset.getEyesImage()

            if img.isValid():
                # Convert bmp binary data into `numpy` array of shape `height x width x channels`
                # so you can for e.g. access the pixels, pass to OpenCV etc.
                # Each element of the `numpy` array is an `np.uint8`.
                # But please note that the images are primarily for Fove researchers and may have preprocessed,
                # have annotations overlayed etc.
                mat = np.array(bitmap.grid(np.array(img.value.image)))
                mat = mat.astype(np.uint8)

                import cv2
                cv2.imshow("eye image", mat)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
                


if __name__ == "__main__":
    main()
