
import itertools
import numpy
import sys
import platform

"""
simple utility functions to know which processor numbers map to the
same physical core, to run code on sibling hyperthreads.

only works for linux unfortunately.
"""

def corelist(allthreads):
        cpulines=open('/proc/cpuinfo').read().split('\n')
        package=None
        core=None
        thread=None

        d=dict()

        package=None
        logical_id=None

        corelist=[]

        for line in cpulines:
                fields=line.split(':')
                try:
                        n=int(fields[1])
                except:
                        continue
                if 'processor' in line:
                        corelist.append(n)
                        logical_id=n
                elif 'physical id' in line:
                        assert package == None
                        package=n
                elif 'core id' in line:
                        assert package != None
                        assert logical_id != None
                        full_core_id=(package,n)
                        if not full_core_id in d:
                                d[full_core_id] = []
                        if allthreads:
                                d[full_core_id].append(logical_id)
                        else:
                                d[full_core_id]=logical_id
                        package=None
                        logical_id=None
                else:
                        continue
        if len(d) > 0:
                return [d[l] for l in sorted(d)]
        n=0
        if platform.machine() == 'aarch64' and len(corelist) == 224:
            print('assuming cavium thunder x2 with 4-way SMT and 2 packages')
            for thread in range(0,224):
                core=thread%28
                package=thread//112
                full_core_id=(package,core)
                if not full_core_id in d:
                    d[full_core_id]=[]
                if allthreads:
                    d[full_core_id].append(thread)
                else:
                    d[full_core_id]=thread
        return [d[l] for l in sorted(d)]

