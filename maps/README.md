# How to run this code

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

## Run go.sh

The python code invokes sudo for two reasons:
  - killall to wipe out other processes of itself that it might have left behind
  - run the sidechannel code which invokes setpriority()

```
sh go.sh
```

## Clean

To clean all data and state information to start over:

```
sh reset.sh
```
