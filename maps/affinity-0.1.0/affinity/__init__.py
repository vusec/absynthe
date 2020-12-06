# Enfold Enterprise Server
# Copyright(C), 2004-5, Enfold Systems, LLC - ALL RIGHTS RESERVED

# Enfold Systems, LLC
# 4617 Montrose Blvd., Suite C215
# Houston, Texas 77006 USA
# p. +1 713.942.2377 | f. +1 832.201.8856
# www.enfoldsystems.com
# info@enfoldsystems.com

import sys
import six

if sys.platform in ('win32',):
    # Use win32process from pywin32
    import win32api
    import win32con
    import win32process
    import pywintypes

    def _get_handle_for_pid(pid, ro=True):
        if pid == 0:
            pHandle = win32process.GetCurrentProcess()
        else:
            flags = win32con.PROCESS_QUERY_INFORMATION
            if not ro:
                flags |= win32con.PROCESS_SET_INFORMATION
            try:
                pHandle = win32api.OpenProcess(flags, 0, pid)
            except pywintypes.error as e:
                six.reraise(ValueError, e)
        return pHandle

    def set_process_affinity_mask(pid, value):
        pHandle = _get_handle_for_pid(pid, False)
        current = win32process.GetProcessAffinityMask(pHandle)[0]
        try:
            win32process.SetProcessAffinityMask(pHandle, value)
        except pywintypes.error as e:
            six.reraise(ValueError, e)
        return current

    def get_process_affinity_mask(pid):
        pHandle = _get_handle_for_pid(pid)
        try:
            return win32process.GetProcessAffinityMask(pHandle)[0]
        except win32process.error as e:
            six.reraise(ValueError, e)

elif sys.platform in ('linux2'):
    # BJG: changed ._affinity to affinity._affinity for python3 without really understanding why it 
    # was broken or why this works
    from affinity._affinity import set_process_affinity_mask, get_process_affinity_mask

else:
    def set_process_affinity_mask(pid, value):
        raise NotImplementedError

    def get_process_affinity_mask(pid):
        raise NotImplementedError
