# How to run this code

## Requirements

For smoothest experience, please run on a new version of
Ubuntu Linux x86-64. I tried it on Ubuntu 20.04.

The code expects 2 cores to be available and HT to be on (so 4
visible processors).

I expect results could be nonsensical when run in a VM (then again,
maybe not, if the hypervisor exposes at least 2 cores and is honest
about the cpu/thread topology), so please try bare metal (first).

This code definitely relies on Linux-isms (e.g. the /proc filesystem),
and to a large extent Debian/Ubuntu-isms, and even more on x86-isms (e.g.
x86 assembly). Porting to adjacent systems may be easy, the less adjacent
the harder to do (cleanly).

## Set up the python environment

This code is written to run on Linux - esp the cpu enumeration code in
cpus.py will need adjustment for a different OS. Other than that there's
no reason we need Linux I think.

We use a virtualenv and set python3.8 to have a bit of a grip on the
dependencies, even though I don't know of any reasons we should need
python3.8. The exact versions used in developing and testing this code
are in `requirements-freeze.txt`.

```
sudo apt-get install python3.8 gcc python3.8-dev virtualenv psmisc xmlstarlet
virtualenv -p python3.8 env
./env/bin/pip install -r requirements.txt
(cd affinity-0.1.0/ && ../env/bin/python setup.py build && ../env/bin/python setup.py install )
```

requirements.txt is the human-friendly version of the python packages. I also did
a 'pip freeze' into requirements-freeze.txt of my working setup if you think you might be running into
package incompatability issues, i.e. for the pip line also try
```
./env/bin/pip install -r requirements-freeze.txt
```
if you think that might help.

## Run go.sh

The python code invokes sudo:
  - to give the sidechannel code executable the CAP_SYS_NICE capability,
    allowing it to invoke setpriority()

Run this script:
```
sh go.sh [uarch]
```
The uarch is optional and is the 3-letter acronym for the arch, e.g. SKL, KBL,
SNB, etc. If not supplied, go.sh tries to detect it.

go.sh then does 3 things:
  1. Collect the interference data on this uarch (can take a long time).
  2. Aggregate the interference data on this uarch in single matrices
  3. Plot the interference data for all uarchs in a single png/pdf

## Clean

To clean all data and state information to start over:

```
sh reset.sh
```
