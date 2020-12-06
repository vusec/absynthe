import cpuid
import sys

long_to_short = {
'broadwell': 'BDW',
'coffeelake': 'CFL',
'coffeelake-avx512': 'CLX',
'cannonlake': 'CNL',
'conroe': 'CON',
'haswell': 'HSW',
'icelake': 'ICL',
'ivybridge': 'IVB',
'kabylake': 'KBL',
'nehalem': 'NHM',
'skylake': 'SKL',
'skylake-avx512': 'SKX',
'sandybridge': 'SNB',
'wolfdale': 'WOL',
'westmere': 'WSM',
'zen+': 'ZEN+',
'zen2': 'ZEN2',
}

short_to_long = { long_to_short[short]: short for short in long_to_short }

if __name__ == "__main__":
   cpu_uarch=cpuid.cpu_microarchitecture()[0]
   if cpu_uarch in long_to_short:
        tla = long_to_short[cpu_uarch]
        print('Found a uarch of %s, TLA is %s.' % (cpu_uarch, tla), file=sys.stderr)
        print('%s' % tla)
        sys.exit(0)

   print('Found a uarch of %s, do not know the TLA for this, sorry.' % cpu_uarch, file=sys.stderr)
   sys.exit(1)

